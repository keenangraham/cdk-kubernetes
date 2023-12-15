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

from constructs import Construct

from shared_infrastructure.cherry_lab.environments import US_WEST_2

from aws_cdk.lambda_layer_kubectl_v27 import KubectlV27Layer


app = App()


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

        Tags.of(
            cluster
        ).add(
            'Name',
            'KubernetesTest',
        )

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



KubernetesStack(
    app,
    'KubernetesStack',
    env=US_WEST_2,
)


app.synth()
