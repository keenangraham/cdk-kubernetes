from datetime import datetime
from pendulum import timezone

from airflow.sdk import dag
from airflow.timetables.simple import CronDataIntervalTimetable

from airflow.providers.cncf.kubernetes.operators.spark_kubernetes import SparkKubernetesOperator


@dag(
    timetable=CronDataIntervalTimetable(
        '0 10 * * *',
        timezone='America/Los_Angeles',
    ),
    start_date=datetime(2026, 5, 1, tzinfo=timezone("America/Los_Angeles")),
    catchup=False,
)
def parse_igvf_logs():
    SparkKubernetesOperator(
        task_id='parse-igvf-logs',
        namespace='data-stack-dev',
        application_file='spark-apps/parse-igvf-logs.yaml',
    )

parse_igvf_logs()
