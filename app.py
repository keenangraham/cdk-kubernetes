import json

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

from aws_cdk.lambda_layer_kubectl_v31 import KubectlV31Layer

from cdk_eks_karpenter import Karpenter

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
            version='2.37.0',
            values={
                'controller': {
                    'serviceAccount': {
                        'create': False
                    }
                },
                'storageClasses': [
                    {
                        'name': 'gp3',
                        'parameters': {
                            'type': 'gp3'
                        },
                        'allowVolumeExpansion': True,
                        'annotations': {
                            'storageclass.kubernetes.io/is-default-class': 'true'
                        }
                    }
                ],
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
            version='3.1.1',
            values={
                'controller': {
                    'serviceAccount': {
                        'create': False
                    }
                }
            }
        )

        chart.node.add_dependency(service_account)


class S3Driver(Construct):

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
            'S3DriverServiceAccount',
            name='s3-csi-driver-sa',
            namespace='kube-system',
        )

        s3_csi_driver_policy = ManagedPolicy.from_managed_policy_arn(
            self,
            'S3CSIDriverPolicy',
            managed_policy_arn='arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess',
        )

        service_account.role.add_managed_policy(s3_csi_driver_policy)

        chart = cluster.add_helm_chart(
            'S3CSIDriver',
            chart='aws-mountpoint-s3-csi-driver',
            repository='https://awslabs.github.io/mountpoint-s3-csi-driver',
            namespace='kube-system',
            version='1.10.0',
            values={
                'node': {
                    'serviceAccount': {
                        'create': False
                    }
                }
            }
        )

        chart.node.add_dependency(service_account)


class SecretsStoreDriver(Construct):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        cluster: Cluster,
        **kwargs: Any
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.chart = cluster.add_helm_chart(
            'SecretsStoreDriver',
            chart='secrets-store-csi-driver',
            repository='https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts',
            namespace='kube-system',
            version='1.4.7',
            values={
                "syncSecret": {
                    "enabled": "true"
                }
            }
        )


class SecretsStoreDriverProviderAws(Construct):

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
            'SecretsStoreCSIDriver',
            chart='secrets-store-csi-driver-provider-aws',
            repository='https://aws.github.io/secrets-store-csi-driver-provider-aws',
            namespace='kube-system',
            version='0.3.10',
        )


class ExternalSecretsOperator(Construct):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        cluster: Cluster,
        **kwargs: Any
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        namespace = 'external-secrets'

        eso_namespace = cluster.add_manifest(
            'ESONamespace',
            {
                'apiVersion': 'v1',
                'kind': 'Namespace',
                'metadata': {
                    "name": namespace,
                },
            }
        )

        chart = cluster.add_helm_chart(
            'ExternalSecretsOperator',
            chart='external-secrets',
            repository='https://charts.external-secrets.io',
            namespace=namespace,
            release='external-secrets',
            version='0.14.2',
        )

        chart.node.add_dependency(eso_namespace)

        password_generator = cluster.add_manifest(
            'ESOPasswordGenerator',
            {
                'apiVersion': 'generators.external-secrets.io/v1alpha1',
                'kind': 'ClusterGenerator',
                'metadata': {
                    'name': 'password-generator',
                    'namespace': namespace
                },
                'spec': {
                    'kind': 'Password',
                    'generator': {
                        'passwordSpec': {                            
                            'length': 42,
                            'digits': 20,
                            'symbols': 0,
                            'noUpper': False,
                            'allowRepeat': True
                        }
                    }
                }
            }
        )

        password_generator.node.add_dependency(eso_namespace)

        password_test = cluster.add_manifest(
            'PasswordTest',
            {
                'apiVersion': 'external-secrets.io/v1beta1',
                'kind': 'ExternalSecret',
                'metadata': {
                    'name': 'generated-secret',
                    'namespace': namespace
                },
                'spec': {
                    'refreshInterval': "0",
                    'target': {
                        'name': 'password-test'
                    },
                    'dataFrom': [
                        {
                            'sourceRef': {
                                'generatorRef': {
                                    'apiVersion': 'generators.external-secrets.io/v1alpha1',
                                    'kind': 'ClusterGenerator',
                                    'name': 'password-generator',
                                }
                            }
                        }
                    ]
                }
            }
        )

        password_test.node.add_dependency(eso_namespace)


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

        self.chart = cluster.add_helm_chart(
            'ExternalDns',
            chart='external-dns',
            repository='https://kubernetes-sigs.github.io/external-dns/',
            namespace='external-dns',
            version='1.15.0',
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

        self.chart.node.add_dependency(service_account)


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


class TestSecretsStoreServiceAccount(Construct):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        cluster: Cluster,
        **kwargs: Any
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        namespace_manifest = cluster.add_manifest(
            'test-secrets-store-ns',
            {
                'apiVersion': 'v1',
                'kind': 'Namespace',
                'metadata': {
                    'name': 'test-secrets-store',
                }
            }
        )

        service_account = cluster.add_service_account(
            'TestSecretsStoreServiceAccount',
            name='test-secrets-store-sa',
            namespace='test-secrets-store',
        )

        service_account.node.add_dependency(namespace_manifest)

        service_account.add_to_principal_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=[
                    'secretsmanager:GetSecretValue',
                    'secretsmanager:DescribeSecret',
                ],
                resources=[
                    'arn:aws:secretsmanager:us-west-2:618537831167:secret:eks-test-secret-GNClRF',
                ],
            )
        )


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
            addon_version='v2.5.0-eksbuild.1',
            resolve_conflicts='OVERWRITE',
        )


class VpcCni(Construct):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        cluster: Cluster,
        **kwargs: Any
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc_cni_cfn_addon = CfnAddon(
            self,
            'VpcCniCfnAddon',
            addon_name='vpc-cni',
            cluster_name=cluster.cluster_name,
            addon_version='v1.19.2-eksbuild.1',
            resolve_conflicts='OVERWRITE',
            configuration_values=json.dumps(
                {
                    "env": {
                        "ENABLE_PREFIX_DELEGATION": "true"
                    }
                }
            )
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


class ArangoDB(Construct):

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
            'ArangoDB',
            chart='kube-arangodb',
            repository='https://arangodb.github.io/kube-arangodb',
            version='1.2.43',
            values={
                'operator': {
                    'features': {
                        'storage': True,
                        'backup': True,
                    }

                },
                'rbac': {
                    'extensions': {
                        'debug': True,
                    }
                }
            }
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
            version='3.12.2',
            namespace='kube-system',
        )


class ClusterAutoscaler(Construct):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        cluster: Cluster,
        **kwargs: Any
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        karpenter = Karpenter(
            self,
            'Karpenter',
            cluster=cluster,
            version='1.2.1',
            namespace='kube-system',
        )
        node_class = karpenter.add_ec2_node_class(
            'nodeclass',
            {
                'subnetSelectorTerms': [
                    {
                        'tags': {
                            'Name': f'{Stack.of(self).stack_name}/Cluster/{cluster.vpc.node.id}/PrivateSubnet*',
                        },
                    },
                ],
                'securityGroupSelectorTerms': [
                    {
                        'tags': {
                            'aws:eks:cluster-name': cluster.cluster_name,
                        },
                    },
                ],
                'role': karpenter.node_role.role_name,
                'amiFamily': 'AL2023',
                'amiSelectorTerms': [
                    {
                        'alias': 'al2023@v20250203'
                    },
                ],
                'kubelet': {
                    'maxPods': 110
                }
            }
        )

        karpenter.add_node_pool(
            'nodepool',
            {
                'template': {
                    'spec': {
                        'nodeClassRef': {
                            'group': 'karpenter.k8s.aws',
                            'kind': 'EC2NodeClass',
                            'name': node_class['name'],
                        },
                        'requirements': [
                            {
                                'key': 'karpenter.k8s.aws/instance-category',
                                'operator': 'In',
                                'values': ['c', 'm', 'r'],
                            },
                            {
                                'key': 'kubernetes.io/arch',
                                'operator': 'In',
                                'values': ['amd64'],
                            },
                            {
                                'key': 'karpenter.k8s.aws/instance-generation',
                                'operator': 'Gt',
                                'values': ['5']
                            },
                        ],
                        'startupTaints': [
                            {
                                'key': 'ebs.csi.aws.com/agent-not-ready',
                                'effect': 'NoExecute',
                            }
                        ]
                    }
                },
                'limits': {
                    'cpu': '48',
                    'memory': '128Gi',
                    'nvidia.com/gpu': '2',
                },
            }
        )


class ArgoCD(Construct):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        cluster: Cluster,
        external_url: str,
        **kwargs: Any
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        chart = cluster.add_helm_chart(
            'ArgoCD',
            chart='argo-cd',
            release='argocd',
            repository='https://argoproj.github.io/argo-helm',
            version='7.7.7',
            namespace='argocd',
            values={
                'configs': {
                    'params': {
                        'server.insecure': True
                    }
                }
            }
        )

        self.manifest = cluster.add_manifest(
            'argocd-ingress',
            {
                'apiVersion': 'networking.k8s.io/v1',
                'kind': 'Ingress',
                'metadata': {
                    'annotations': {
                        'alb.ingress.kubernetes.io/listen-ports': '[{\"HTTP\": 80}, {\"HTTPS\":443}]',
                        'alb.ingress.kubernetes.io/scheme': 'internet-facing',
                        'alb.ingress.kubernetes.io/ssl-redirect': '443',
                        'alb.ingress.kubernetes.io/target-type': 'ip',
                    },
                    'name': 'argocd-ingress',
                    'namespace': 'argocd',
                },
                'spec': {
                    'ingressClassName': 'alb',
                    'rules': [
                        {
                            'host': external_url,
                            'http': {
                                'paths': [
                                    {
                                        'backend': {
                                            'service': {
                                                'name': 'argocd-server',
                                                'port': {
                                                    'number': 80
                                                }
                                            }
                                        },
                                        'path': '/',
                                        'pathType': 'Prefix'
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        )

        self.manifest.node.add_dependency(chart)
        self.manifest.node.add_dependency(cluster.alb_controller)


spark_aws_secret_objects = """- objectName: "test/spark/read-cross-acccount-bucket"
  objecttype: "secretsmanager"
  jmesPath:
    - path: "ACCESS_KEY"
      objectAlias: "ACCESS_KEY"
    - path: "SECRET_ACCESS_KEY"
      objectAlias: "SECRET_ACCESS_KEY"
"""


class SparkBucketReadServiceAccount(Construct):

    def __init__(self, scope: Construct, construct_id: str, *, cluster: Cluster, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        NAMESPACE = 'data-stack-dev'

        namespace_manifest = cluster.add_manifest(
            f'{NAMESPACE}-ns',
            {
                'apiVersion': 'v1',
                'kind': 'Namespace',
                'metadata': {
                    'name': NAMESPACE
                }
            }
        )

        service_account = cluster.add_service_account(
            'SparkBucketReadServiceAccount',
            name='spark-bucket-read-sa',
            namespace=NAMESPACE,
        )

        service_account.node.add_dependency(namespace_manifest)

        spark_bucket_read_policy = ManagedPolicy.from_managed_policy_arn(
            self,
            'SparkBucketReadPolicy',
            managed_policy_arn='arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess',
        )

        service_account.role.add_managed_policy(spark_bucket_read_policy)

        service_account.add_to_principal_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=[
                    'secretsmanager:GetSecretValue',
                    'secretsmanager:DescribeSecret',
                ],
                resources=[
                    'arn:aws:secretsmanager:us-west-2:618537831167:secret:test/spark/read-cross-acccount-bucket-TBr0Gs'
                ],
            )
        )

        service_account.add_to_principal_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=[
                    's3:GetObject',
                    's3:PutObject',
                    's3:DeleteObject',
                    's3:ListBucket'
                ],
                resources=[
                    'arn:aws:s3:::spark-log-parsing-test',
                    'arn:aws:s3:::spark-log-parsing-test/*'
                ]
            )
        )

        service_account.add_to_principal_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=[
                    's3:Get*',
                    's3:ListBucket'
                ],
                resources=[
                    'arn:aws:s3:::encode-public-logs',
                    'arn:aws:s3:::encode-public-logs/*'
                ]
            )
        )

        service_account.add_to_principal_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=[
                    '*',
                ],
                resources=[
                    'arn:aws:s3:::airflow-k8s-logging',
                    'arn:aws:s3:::airflow-k8s-logging/*'
                ],
            )
        )

        secrets_provider = cluster.add_manifest(
            'spark-aws-secrets-provider',
            {
                "apiVersion": "secrets-store.csi.x-k8s.io/v1",
                "kind": "SecretProviderClass",
                "metadata": {
                    "name": "spark-aws-secrets",
                    "namespace": NAMESPACE
                },
                "spec": {
                    "provider": "aws",
                    "parameters": {
                        "objects": spark_aws_secret_objects
                    },
                    "secretObjects": [
                        {
                            "secretName": "aws-spark-access-key",
                            "data": [
                                {
                                    "objectName": "ACCESS_KEY",
                                    "key": "ACCESS_KEY"
                                }
                            ],
                            "type": "Opaque"
                        },
                        {
                            "secretName": "aws-spark-secret-access-key",
                            "data": [
                                {
                                    "objectName": "SECRET_ACCESS_KEY",
                                    "key": "SECRET_ACCESS_KEY"
                                }
                            ],
                            "type": "Opaque"
                        }
                    ],
                }
            }
        )

        secrets_provider.node.add_dependency(namespace_manifest)

        read_role = cluster.add_manifest(
            'spark-bucket-read-role',
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "Role",
                "metadata": {
                    "name": "spark-bucket-read-role",
                    "namespace": NAMESPACE
                },
                "rules": [
                    {
                        "apiGroups": [""],
                        "resources": ["pods", "configmaps", "persistentvolumeclaims", "services"],
                        "verbs": ["get", "list", "watch", "create", "update", "patch", "delete", "deletecollection"]
                    }
                ]
            }
        )

        read_role.node.add_dependency(namespace_manifest)

        role_binding = cluster.add_manifest(
            'spark-bucket-read-rolebinding',
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "RoleBinding",
                "metadata": {
                    "name": "spark-bucket-read-rolebinding",
                    "namespace": NAMESPACE
                },
                "roleRef": {
                    "apiGroup": "rbac.authorization.k8s.io",
                    "kind": "Role",
                    "name": "spark-bucket-read-role"
                },
                "subjects": [
                    {
                        "kind": "ServiceAccount",
                        "name": "spark-bucket-read-sa",
                        "namespace": NAMESPACE
                    }
                ]
            }
        )

        role_binding.node.add_dependency(namespace_manifest)

        airflow_static_webserver_secret = cluster.add_manifest(
            'AirflowStaticWebserverSecret',
            {
                'apiVersion': 'external-secrets.io/v1beta1',
                'kind': 'ExternalSecret',
                'metadata': {
                    'name': 'airflow-static-webserver-secret-eso',
                    'namespace': NAMESPACE
                },
                'spec': {
                    'refreshInterval': "0",
                    'target': {
                        'name': 'airflow-static-webserver-secret-generated',
                        'template': {
                            'data': {
                                'webserver-secret-key': '{{ .password }}'
                            }
                        }
                    },
                    'dataFrom': [
                        {
                            'sourceRef': {
                                'generatorRef': {
                                    'apiVersion': 'generators.external-secrets.io/v1alpha1',
                                    'kind': 'ClusterGenerator',
                                    'name': 'password-generator',
                                }
                            }
                        }
                    ]
                }
            }
        )

        airflow_static_webserver_secret.node.add_dependency(namespace_manifest)


class AirflowLoggingServiceAccount(Construct):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        cluster: Cluster,
        **kwargs: Any
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        NAMESPACE = 'data-stack-dev'

        service_account = cluster.add_service_account(
            'AirflowLoggingServiceAccount',
            name='airflow-logging-sa',
            namespace=NAMESPACE,
        )

        service_account.add_to_principal_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=[
                    's3:ListAllMyBuckets',
                ],
                resources=['*'],
            )
        )

        service_account.add_to_principal_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=[
                    '*',
                ],
                resources=[
                    'arn:aws:s3:::airflow-k8s-logging',
                    'arn:aws:s3:::airflow-k8s-logging/*'
                ],
            )
        )

        # add kubernetes RBAC for using spark operator from this service account
        spark_role = cluster.add_manifest(
            'spark-operator-role',
            {
                'apiVersion': 'rbac.authorization.k8s.io/v1',
                'kind': 'Role',
                'metadata': {
                    'name': 'spark-operator-role',
                    'namespace': NAMESPACE
                },
                'rules': [
                    {
                        'apiGroups': ['sparkoperator.k8s.io'],
                        'resources': [
                            'sparkapplications',
                            'sparkapplications/status',
                            'sparkapplications/finalizers'
                        ],
                        'verbs': ['create', 'delete', 'deletecollection', 'get', 'list', 'patch', 'update', 'watch']
                    },
                    {
                        'apiGroups': [''],
                        'resources': ['pods', 'services', 'configmaps', 'secrets'],
                        'verbs': ['create', 'delete', 'deletecollection', 'get', 'list', 'patch', 'update', 'watch']
                    }
                ]
            }
        )
        
        spark_role_binding = cluster.add_manifest(
            'spark-operator-rolebinding',
            {
                'apiVersion': 'rbac.authorization.k8s.io/v1',
                'kind': 'RoleBinding',
                'metadata': {
                    'name': 'spark-operator-rolebinding',
                    'namespace': NAMESPACE
                },
                'subjects': [
                    {
                        'kind': 'ServiceAccount',
                        'name': 'airflow-logging-sa',
                        'namespace': NAMESPACE
                    }
                ],
                'roleRef': {
                    'kind': 'Role',
                    'name': 'spark-operator-role',
                    'apiGroup': 'rbac.authorization.k8s.io'
                }
            }
        )
        
        spark_role_binding.node.add_dependency(spark_role)
        spark_role_binding.node.add_dependency(service_account)


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
            version=KubernetesVersion.V1_31,
            kubectl_layer=KubectlV31Layer(
                self,
                'kubectl',
            ),
            alb_controller=AlbControllerOptions(
                version=AlbControllerVersion.V2_8_2,
            ),
            masters_role=kubernetes_admin_role,
            default_capacity=2,
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

        s3_driver = S3Driver(
            self,
            'S3Driver',
            cluster=cluster,
        )

        secrets_store_driver = SecretsStoreDriver(
            self,
            'SecretsStoreDriver',
            cluster=cluster,
        )

        secrets_store_driver_provider_aws = SecretsStoreDriverProviderAws(
            self,
            'SecretsStoreDriverProviderAws',
            cluster=cluster,
        )

        external_secrets_operator = ExternalSecretsOperator(
            self,
            'ExternalSecretsOperator',
            cluster=cluster,
        )

        cloudwatch_observability = CloudWatchObservability(
            self,
            'CloudwatchObservability',
            cluster=cluster
        )

        vpc_cni = VpcCni(
            self,
            'VpcCni',
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

        argocd = ArgoCD(
            self,
            'ArgoCD',
            cluster=cluster,
            external_url='argocd.api.encodedcc.org',
        )

        argocd.manifest.node.add_dependency(
            external_dns.chart
        )

        cluster_autoscaler = ClusterAutoscaler(
            self,
            'ClusterAutoscaler',
            cluster=cluster,
        )

        arangodb = ArangoDB(
            self,
            'ArangoDB',
            cluster=cluster,
        )

        test_secrets_store_service_account = TestSecretsStoreServiceAccount(
            self,
            'TestSecretsStoreServiceAccount',
            cluster=cluster,
        )

        spark_bucket_read_service_account = SparkBucketReadServiceAccount(
            self,
            'SparkBucketReadServiceAccount',
            cluster=cluster,
        )

        airflow_logging_service_account = AirflowLoggingServiceAccount(
            self,
            'AirflowLoggingServiceAccount',
            cluster=cluster,
        )


KubernetesStack(
    app,
    'KubernetesStack3',
    env=US_WEST_2,
)


app.synth()
