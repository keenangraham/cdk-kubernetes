from aws_cdk import App
from aws_cdk import Stack
from aws_cdk import RemovalPolicy
from aws_cdk import CfnOutput
from aws_cdk import CustomResource
from aws_cdk import Duration

from aws_cdk.aws_eks import Cluster
from aws_cdk.aws_eks import KubernetesVersion

from constructs import Construct

from shared_infrastructure.cherry_lab.environments import US_WEST_2

from aws_cdk.lambda_layer_kubectl_v27 import KubectlV27Layer


app = App()


class KubernetesStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cluster = Cluster(
            self,
            'Cluster',
            version=KubernetesVersion.V1_27,
            kubectl_layer=KubectlV27Layer(
                self,
                'kubectl',
            )
        )

        cluster.add_manifest(
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
                                    'container_port': 8080
                                }
                            ]
                        },
                    ]
                }
            },
        )


KubernetesStack(
    app,
    'KubernetesStack',
    env=US_WEST_2,
)


app.synth()
