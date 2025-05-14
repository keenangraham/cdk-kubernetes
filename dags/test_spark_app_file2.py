from datetime import datetime, timedelta
from pathlib import Path

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

# Define path to your Spark application YAML
# This assumes the DAG file is in a structure like airflow/dags/ and the YAML is in the repo
# REPO_ROOT = Path(__file__).parents[2]  # Adjust based on your folder structure
# SPARK_APP_YAML_PATH = str(REPO_ROOT / "k8s/spark-apps/test-spark-app.yaml")


with DAG(
    dag_id='test-spark-app-file',
    default_args=default_args,
    description='A DAG to run Spark on Kubernetes',
    schedule_interval=timedelta(days=1),
    catchup=False,
) as dag:

    # Use the application_file parameter to directly point to the YAML file
    spark_task = SparkKubernetesOperator(
        task_id='spark_task_from_file',
        namespace='data-stack-dev',
        application_file='spark-apps/test-spark-app.yaml',
    )