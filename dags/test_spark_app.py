from datetime import datetime, timedelta

from airflow import DAG

from airflow.providers.cncf.kubernetes.operators.spark_kubernetes import SparkKubernetesOperator


default_args = {
    'owner': 'me',
    'depends_on_past': False,
    'start_date': datetime(2025, 2, 4),
    'retries': 1,
    'schedule': None,
    'retry_delay': timedelta(minutes=5),
}


spark_app = {
  "apiVersion": "sparkoperator.k8s.io/v1beta2",
  "kind": "SparkApplication",
  "metadata": {
    "name": "test-spark",
    "namespace": "data-stack-dev"
  },
  "spec": {
    "type": "Python",
    "pythonVersion": "3",
    "mode": "cluster",
    "image": "public.ecr.aws/cherry-lab/cherry-lab:spark-3.5.4-s3",
    "imagePullPolicy": "IfNotPresent",
    "mainApplicationFile": "https://raw.githubusercontent.com/keenangraham/cdk-kubernetes/refs/heads/main/spark/test-spark.py",
    "sparkVersion": "3.5.3",
    "driver": {
      "labels": {
          "app.kubernetes.io/name": "test-spark-app"
      },
      "coreRequest": "1000m",
      "memory": "2048M",
      "serviceAccount": "spark-bucket-read-sa",
      "env": [
        {
          "name": "IVY_CACHE_DIR",
          "value": "/tmp/.ivy2"
        },
        {
          "name": "AWS_ACCESS_KEY_ID",
          "valueFrom": {
            "secretKeyRef": {
              "name": "aws-spark-access-key",
              "key": "ACCESS_KEY"
            }
          }
        },
        {
          "name": "AWS_SECRET_ACCESS_KEY",
          "valueFrom": {
            "secretKeyRef": {
              "name": "aws-spark-secret-access-key",
              "key": "SECRET_ACCESS_KEY"
            }
          }
        }
      ],
      "volumeMounts": [
        {
          "name": "ivy-cache",
          "mountPath": "/tmp/.ivy2"
        },
        {
          "name": "aws-creds",
          "mountPath": "/tmp/.aws-creds"
        }
      ]
    },
    "executor": {
      "instances": 1,
      "coreRequest": "100m",
      "memory": "512M",
      "serviceAccount": "spark-bucket-read-sa",
      "env": [
        {
          "name": "AWS_ACCESS_KEY_ID",
          "valueFrom": {
            "secretKeyRef": {
              "name": "aws-spark-access-key",
              "key": "ACCESS_KEY"
            }
          }
        },
        {
          "name": "AWS_SECRET_ACCESS_KEY",
          "valueFrom": {
            "secretKeyRef": {
              "name": "aws-spark-secret-access-key",
              "key": "SECRET_ACCESS_KEY"
            }
          }
        }
      ],
      "volumeMounts": [
        {
          "name": "aws-creds",
          "mountPath": "/tmp/.aws-creds"
        }
      ]
    },
    "dynamicAllocation": {
      "enabled": True,
      "initialExecutors": 1,
      "maxExecutors": 10,
      "minExecutors": 1
    },
    "volumes": [
      {
        "name": "ivy-cache",
        "emptyDir": {}
      },
      {
        "name": "aws-creds",
        "csi": {
          "driver": "secrets-store.csi.k8s.io",
          "readOnly": True,
          "volumeAttributes": {
            "secretProviderClass": "spark-aws-secrets"
          }
        }
      }
    ]
  }
}


with DAG(
    dag_id='test-spark-app',
    default_args=default_args,
    description='A DAG to run Spark on Kubernetes',
    schedule_interval=timedelta(days=1),
    catchup=False,
) as dag:


    spark_task = SparkKubernetesOperator(
        task_id='spark_task',
        namespace='data-stack-dev',
        template_spec=spark_app,
        executor_config={
            'KubernetesExecutor': {
                'service_account_name': 'airflow-logging-sa',
                'namespace': 'data-stack-dev'
            }
        }
    )
