from aws_cdk import App
from aws_cdk import Stack
from aws_cdk import RemovalPolicy
from aws_cdk import CfnOutput
from aws_cdk import CustomResource
from aws_cdk import Duration
from aws_cdk import Tags

from aws_cdk.aws_iam import AccountRootPrincipal
from aws_cdk.aws_iam import Role
from aws_cdk.aws_iam import PolicyStatement
from aws_cdk.aws_iam import ManagedPolicy

from aws_cdk.aws_eks import Cluster
from aws_cdk.aws_eks import KubernetesVersion
from aws_cdk.aws_eks import AlbControllerOptions
from aws_cdk.aws_eks import AlbControllerVersion
from aws_cdk.aws_eks import CapacityType

from aws_cdk.aws_ec2 import InstanceType

from constructs import Construct

from shared_infrastructure.cherry_lab.environments import US_WEST_2

from aws_cdk.lambda_layer_kubectl_v27 import KubectlV27Layer

from typing import Any

app = App()


class EBSDriver(Construct):

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            *,
            cluster: Cluster,
            **kwargs: Any
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cluster.add_helm_chart(
            'EBSCSIDriver',
            chart='aws-ebs-csi-driver',
            repository='https://kubernetes-sigs.github.io/aws-ebs-csi-driver',
            namespace='kube-system',
            version='2.25.0',
        )

        ebs_csi_driver_policy = ManagedPolicy.from_managed_policy_arn(
            self,
            'EBSCSIDriverPolicy',
            managed_policy_arn='arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy'
        )

        cluster.default_nodegroup.role.add_managed_policy(ebs_csi_driver_policy)


class EFSDriver(Construct):

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            *,
            cluster: Cluster,
            **kwargs: Any
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cluster.add_helm_chart(
            'EFSCSIDriver',
            chart='aws-efs-csi-driver',
            repository='https://kubernetes-sigs.github.io/aws-efs-csi-driver',
            namespace='kube-system',
            version='2.5.2',
        )

        efs_csi_driver_policy = ManagedPolicy.from_managed_policy_arn(
            self,
            'EFSCSIDriverPolicy',
            managed_policy_arn='arn:aws:iam::aws:policy/service-role/AmazonEFSCSIDriverPolicy'
        )

        cluster.default_nodegroup.role.add_managed_policy(efs_csi_driver_policy)


class TestApp(Construct):

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            *,
            cluster: Cluster,
            **kwargs: Any
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        manifest = cluster.add_manifest(
            'testpod',
            {
                'apiVersion': 'v1',
                'kind': 'Pod',
                'metadata': {
                    'name': 'testpod',
                },
                'spec': {
                    'containers': [
                        {
                            'name': 'testcontainer',
                            'image': 'paulbouwer/hello-kubernetes:1.5',
                            'ports': [
                                {
                                    'containerPort': 8080
                                }
                            ]
                        },
                    ]
                }
            },
        )

        manifest.node.add_dependency(cluster.alb_controller)



class KubernetesStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        kubernetes_admin_role = Role(
            self,
            'KubernetesAdminRole',
            assumed_by=AccountRootPrincipal(),
        )

        kubernetes_admin_role.add_to_policy(
            PolicyStatement(
                actions=[
                    'eks:AccessKubernetesApi',
                    'eks:Describe*',
                    'eks:List*',
                ],
                resources=['*']
            )
        )

        cluster = Cluster(
            self,
            'Cluster',
            version=KubernetesVersion.V1_27,
            kubectl_layer=KubectlV27Layer(
                self,
                'kubectl',
            ),
            alb_controller=AlbControllerOptions(
                version=AlbControllerVersion.V2_5_1,
            ),
            masters_role=kubernetes_admin_role,
        )

        cluster.add_nodegroup_capacity(
            'more-nodes',
            min_size=1,
            max_size=2,
            disk_size=10,
            capacity_type=CapacityType.SPOT,
            instance_types=[
                InstanceType('m5.large'),
            ],
        )

        Tags.of(
            cluster
        ).add(
            'Name',
            'KubernetesTest',
        )

        test_app = TestApp(
            self,
            'TestApp',
            cluster=cluster,
        )

        ebs_driver = EBSDriver(
            self,
            'EBSDriver',
            cluster=cluster,
        )

        efs_driver = EFSDriver(
            self,
            'EFSDriver',
            cluster=cluster,
        )



KubernetesStack(
    app,
    'KubernetesStack',
    env=US_WEST_2,
)


app.synth()
