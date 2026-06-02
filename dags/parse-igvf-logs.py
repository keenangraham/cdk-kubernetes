from datetime import datetime

from airflow.sdk import dag
from airflow.sdk import task

from airflow.providers.cncf.kubernetes.operators.spark_kubernetes import SparkKubernetesOperator


@dag(
    schedule='@daily',
    start_date=datetime(2026, 5, 1),
    catchup=False,
)
def parse_igvf_logs():

    @task
    def launch_spark_job():
        spark_task = SparkKubernetesOperator(
            task_id='parse-igvf-logs',
            namespace='data-stack-dev',
            application_file='spark-apps/parse-igvf-logs.yaml',
        )

    launch_spark_job()

parse_igvf_logs()
