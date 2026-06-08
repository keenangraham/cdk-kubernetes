import base64
from datetime import datetime
from pendulum import timezone

from airflow.sdk import dag
from airflow.timetables.interval import CronDataIntervalTimetable
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from kubernetes.client import V1EnvVar, V1EnvVarSource, V1SecretKeySelector

_LOAD_SCRIPT = """
import clickhouse_connect
import os
import sys

date = sys.argv[1]
aws_key = os.environ['AWS_ACCESS_KEY_ID']
aws_secret = os.environ['AWS_SECRET_ACCESS_KEY']
ch_password = os.environ['CLICKHOUSE_PASSWORD']

client = clickhouse_connect.get_client(
    host='clickhouse',
    port=8123,
    username='default',
    password=ch_password,
)

client.command('CREATE DATABASE IF NOT EXISTS igvf_logs')

client.command('''
    CREATE TABLE IF NOT EXISTS igvf_logs.s3_access_logs (
        bucket_owner     String,
        bucket_name      String,
        timestamp        String,
        remote_ip        String,
        requester        String,
        request_id       String,
        operation        String,
        key              String,
        request_uri      String,
        http_status      String,
        error_code       String,
        bytes_sent       String,
        object_size      String,
        total_time       String,
        turn_around_time String,
        referrer         String,
        user_agent       String,
        version_id       String,
        date             Date
    )
    ENGINE = MergeTree()
    PARTITION BY date
    ORDER BY (date, request_id)
''')

client.command(f"ALTER TABLE igvf_logs.s3_access_logs DROP PARTITION IF EXISTS '{date}'")

client.command(f'''
    INSERT INTO igvf_logs.s3_access_logs
    SELECT
        bucket_owner, bucket_name, timestamp, remote_ip, requester,
        request_id, operation, key, request_uri, http_status, error_code,
        bytes_sent, object_size, total_time, turn_around_time, referrer,
        user_agent, version_id,
        toDate('{date}')
    FROM s3(
        's3://igvf-parsed-logs/parquet/date={date}/*.parquet',
        '{aws_key}', '{aws_secret}',
        'Parquet'
    )
''')

print(f'Loaded logs for {date}')
"""

_SCRIPT_B64 = base64.b64encode(_LOAD_SCRIPT.encode()).decode()


@dag(
    schedule=CronDataIntervalTimetable(
        '0 14 * * *',
        timezone='America/Los_Angeles',
    ),
    start_date=datetime(2026, 5, 1, tzinfo=timezone("America/Los_Angeles")),
    catchup=False,
)
def load_igvf_logs_to_clickhouse():
    KubernetesPodOperator(
        task_id='load-igvf-logs-to-clickhouse',
        namespace='data-stack-dev',
        image='python:3.12-slim',
        cmds=['bash', '-c'],
        arguments=[
            f"pip install -q clickhouse-connect && "
            f"python -c \"import base64,sys; exec(base64.b64decode(b'{_SCRIPT_B64}').decode())\" {{{{ ds }}}}"
        ],
        env_vars=[
            V1EnvVar(
                name='AWS_ACCESS_KEY_ID',
                value_from=V1EnvVarSource(
                    secret_key_ref=V1SecretKeySelector(
                        name='aws-spark-access-key',
                        key='ACCESS_KEY',
                    ),
                ),
            ),
            V1EnvVar(
                name='AWS_SECRET_ACCESS_KEY',
                value_from=V1EnvVarSource(
                    secret_key_ref=V1SecretKeySelector(
                        name='aws-spark-secret-access-key',
                        key='SECRET_ACCESS_KEY',
                    ),
                ),
            ),
            V1EnvVar(
                name='CLICKHOUSE_PASSWORD',
                value_from=V1EnvVarSource(
                    secret_key_ref=V1SecretKeySelector(
                        name='clickhouse-password',
                        key='password',
                    ),
                ),
            ),
        ],
        on_finish_action='delete_pod',
    )


load_igvf_logs_to_clickhouse()
