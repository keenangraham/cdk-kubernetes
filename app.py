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
from aws_cdk.aws_iam import User
from aws_cdk.aws_iam import Effect

from aws_cdk.aws_eks import Cluster
from aws_cdk.aws_eks import KubernetesVersion
from aws_cdk.aws_eks import AlbControllerOptions
from aws_cdk.aws_eks import AlbControllerVersion
from aws_cdk.aws_eks import CapacityType
from aws_cdk.aws_eks import CfnAddon
from aws_cdk.aws_eks import ServiceAccount

from aws_cdk.aws_sqs import Queue

from aws_cdk.aws_ec2 import InstanceType

from aws_cdk.aws_route53 import HostedZone

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

        service_account = cluster.add_service_account(
            'EBSDriverServiceAccount',
            name='ebs-csi-controller-sa',
            namespace='kube-system',
        )

        ebs_csi_driver_policy = ManagedPolicy.from_managed_policy_arn(
            self,
            'EBSCSIDriverPolicy',
            managed_policy_arn='arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy'
        )

        service_account.role.add_managed_policy(ebs_csi_driver_policy)

        chart = cluster.add_helm_chart(
            'EBSCSIDriver',
            chart='aws-ebs-csi-driver',
            repository='https://kubernetes-sigs.github.io/aws-ebs-csi-driver',
            namespace='kube-system',
            version='2.25.0',
            values={
                'controller': {
                    'serviceAccount': {
                        'create': False
                    }
                }
            }
        )

        chart.node.add_dependency(service_account)



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

        service_account = cluster.add_service_account(
            'EFSDriverServiceAccount',
            name='efs-csi-controller-sa',
            namespace='kube-system',
        )

        efs_csi_driver_policy = ManagedPolicy.from_managed_policy_arn(
            self,
            'EFSCSIDriverPolicy',
            managed_policy_arn='arn:aws:iam::aws:policy/service-role/AmazonEFSCSIDriverPolicy'
        )

        service_account.role.add_managed_policy(efs_csi_driver_policy)

        chart = cluster.add_helm_chart(
            'EFSCSIDriver',
            chart='aws-efs-csi-driver',
            repository='https://kubernetes-sigs.github.io/aws-efs-csi-driver',
            namespace='kube-system',
            version='2.5.2',
            values={
                'controller': {
                    'serviceAccount': {
                        'create': False
                    }
                }
            }
        )

        chart.node.add_dependency(service_account)


class ExternalDns(Construct):

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
            'externaldns-ns',
            {
                'apiVersion': 'v1',
                'kind': 'Namespace',
                'metadata': {
                    'name': 'external-dns',
                }
            }
        )

        service_account = cluster.add_service_account(
            'ExternalDnsServiceAccount',
            name='external-dns-sa',
            namespace='external-dns',
        )

        service_account.node.add_dependency(manifest)

        service_account.add_to_principal_policy(
             PolicyStatement(
                effect=Effect.ALLOW,
                actions=[
                    'route53:ChangeResourceRecordSets',
                    'route53:ListResourceRecordSets'
                ],
                resources=[
                    HostedZone.from_hosted_zone_id(
                        self,
                        'ApiEncodeDccOrg',
                        'Z100726339CN2ETJI2S55',
                    ).hosted_zone_arn
                ]
            )
        )

        service_account.add_to_principal_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=[
                    'route53:ListHostedZones'
                ],
                resources=[
                    '*'
                ]
            )
        )

        chart = cluster.add_helm_chart(
            'ExternalDns',
            chart='external-dns',
            repository='https://kubernetes-sigs.github.io/external-dns/',
            namespace='external-dns',
            version='1.13.1',
            values={
                'serviceAccount': {
                    'create': False,
                    'name': 'external-dns-sa',
                    'annotations': {
                        'eks.amazonaws.com/role-arn': service_account.role.role_arn
                    }
                },
                'policy': 'sync'
            }
        )

        chart.node.add_dependency(service_account)


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


class PythonApp(Construct):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        cluster: Cluster,
        queue: Queue,
        **kwargs: Any
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        service_account = cluster.add_service_account(
            'PythonServiceAccount',
            name='python-sa',
        )

        queue.grant_send_messages(
            service_account
        )

        queue.grant_consume_messages(
            service_account
        )

        manifest = cluster.add_manifest(
            'pythonapp',
            {
                'apiVersion': 'apps/v1',
                'kind': 'Deployment',
                'metadata': {
                    'name': 'python-deployment',
                    'labels': {
                        'app': 'python'
                    }
                },
                'spec': {
                    'replicas': 1,
                    'selector': {
                        'matchLabels': {
                            'app': 'python'
                        }
                    },
                    'template': {
                        'metadata': {
                            'labels': {
                                'app': 'python'
                            }
                        },
                        'spec': {
                            'serviceAccountName': 'python-sa',
                            'containers': [
                                {
                                    'name': 'python',
                                    'image': 'python:3.12.1-bullseye',
                                    'command': ['/bin/sh', '-c', 'tail -f /dev/null'],
                                    'env': [
                                        {
                                            'name': 'QUEUE_URL',
                                            'value': queue.queue_url,
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                }
            }
        )

        manifest.node.add_dependency(
            service_account
        )
        manifest.node.add_dependency(
            queue
        )


class CloudWatchObservability(Construct):

    def __init__(
            self,
        scope: Construct,
        construct_id: str,
        *,
        cluster: Cluster,
        **kwargs: Any
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        aws_xray_write_only_access = ManagedPolicy.from_managed_policy_arn(
            self,
            'AwsXrayWriteOnlyAccess',
            managed_policy_arn='arn:aws:iam::aws:policy/AWSXrayWriteOnlyAccess',
        )

        cloudwatch_agent_server_policy = ManagedPolicy.from_managed_policy_arn(
            self,
            'CloudwatchAgenetServerPolicy',
            managed_policy_arn='arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy',
        )

        cluster.default_nodegroup.role.add_managed_policy(aws_xray_write_only_access)
        cluster.default_nodegroup.role.add_managed_policy(cloudwatch_agent_server_policy)

        amazon_cloudwatch_observability_cfn_addon = CfnAddon(
            self,
            'AmazonCloudwatchObservabilityCfnAddon',
            addon_name='amazon-cloudwatch-observability',
            cluster_name=cluster.cluster_name,
            addon_version='v1.1.1-eksbuild.1',
            resolve_conflicts='OVERWRITE',
        )


class ClusterPermissions(Construct):

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
            'ReadOnlyAdminClusterRoleBinding',
            {
                'apiVersion': 'rbac.authorization.k8s.io/v1',
                'kind': 'ClusterRoleBinding',
                'metadata': {
                    'name': 'read-only-admin',
                },
                'roleRef': {
                    'apiGroup': 'rbac.authorization.k8s.io',
                    'kind': 'ClusterRole',
                    'name': 'view'
                },
                'subjects': [
                    {
                        'apiGroup': 'rbac.authorization.k8s.io',
                        'kind': 'Group',
                        'name': 'read-only-admin'
                    }
                ]
            }
        )

        users = [
            'keenangraham',
            'ojolanki',
        ]

        for user in users:
           cluster.aws_auth.add_user_mapping(
               User.from_user_name(
                   self,
                   f'User-{user}',
                   user_name=user,
            ),
            groups=[
                'read-only-admin',
            ]
        )


class MetricsServer(Construct):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        cluster: Cluster,
        **kwargs: Any
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        chart = cluster.add_helm_chart(
            'MetricsServer',
            chart='metrics-server',
            repository='https://kubernetes-sigs.github.io/metrics-server',
            version='3.11.0',
            namespace='kube-system',
        )


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

        cluster_permissions = ClusterPermissions(
            self,
            'ClusterPermissions',
            cluster=cluster,
        )

        cluster.add_nodegroup_capacity(
            'more-nodes',
            min_size=0,
            max_size=1,
            desired_size=0,
            disk_size=10,
            capacity_type=CapacityType.SPOT,
            instance_types=[
                InstanceType('m5.large'),
            ],
            node_role=cluster.default_nodegroup.role,
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

        cloudwatch_observability = CloudWatchObservability(
            self,
            'CloudwatchObservability',
            cluster=cluster
        )

        metrics_server = MetricsServer(
            self,
            'MetricsServer',
            cluster=cluster,
        )

        queue = Queue(
            self,
            'TestEksQueue',
        )

        python_app = PythonApp(
            self,
            'PythonApp',
            cluster=cluster,
            queue=queue,
        )

        external_dns = ExternalDns(
            self,
            'ExternalDns',
            cluster=cluster,
        )


KubernetesStack(
    app,
    'KubernetesStack',
    env=US_WEST_2,
)


app.synth()
