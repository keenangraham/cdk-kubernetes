from datetime import datetime, timedelta
from pendulum import timezone

from airflow.sdk import dag
from airflow.timetables.interval import CronDataIntervalTimetable

from airflow.providers.cncf.kubernetes.operators.spark_kubernetes import SparkKubernetesOperator


@dag(
    schedule=CronDataIntervalTimetable(
        '0 4 * * *',
        timezone='America/Los_Angeles',
    ),
    start_date=datetime(2026, 5, 1, tzinfo=timezone("America/Los_Angeles")),
    catchup=False,
)
def parse_encode_logs():
    SparkKubernetesOperator(
        task_id='parse-encode-logs',
        namespace='data-stack-dev',
        application_file='spark-apps/parse-encode-logs.yaml',
        delete_on_termination=False,
        retries=1,
        retry_delay=timedelta(minutes=2),
    )

parse_encode_logs()
