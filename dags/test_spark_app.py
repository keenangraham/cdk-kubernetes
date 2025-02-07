from datetime import datetime, timedelta

from airflow import DAG

from airflow.providers.cncf.kubernetes.operators.spark_kubernetes import SparkKubernetesOperator


default_args = {
    'owner': 'me',
    'depends_on_past': False,
    'start_date': datetime(2025, 2, 4),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


spark_app = {
  "apiVersion": "sparkoperator.k8s.io/v1beta2",
  "kind": "SparkApplication",
  "metadata": {
    "name": "test-spark",
  },
  "spec": {
    "type": "Python",
    "pythonVersion": "3",
    "mode": "cluster",
    "image": "public.ecr.aws/cherry-lab/cherry-lab:spark-3.5.4-s3",
    "imagePullPolicy": "IfNotPresent",
    "mainApplicationFile": "https://raw.githubusercontent.com/keenangraham/cdk-kubernetes/refs/heads/main/spark/test-spark-simple.py",
    "sparkVersion": "3.5.3",
    "driver": {
      "coreRequest": "1000m",
      "memory": "2048M"
    },
    "executor": {
      "instances": 1,
      "coreRequest": "100m",
      "memory": "512M"
    },
    "dynamicAllocation": {
      "enabled": True,
      "initialExecutors": 1,
      "maxExecutors": 10,
      "minExecutors": 1
    }
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
        template_spec=spark_app
    )
