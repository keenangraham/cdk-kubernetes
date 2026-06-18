from datetime import datetime
from pendulum import timezone

from airflow.sdk import dag
from airflow.timetables.interval import CronDataIntervalTimetable
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from kubernetes.client import V1EnvVar, V1EnvVarSource, V1SecretKeySelector, V1EnvFromSource, V1SecretEnvSource

_SCRIPT_URL = (
    'https://raw.githubusercontent.com/keenangraham/cdk-kubernetes'
    '/refs/heads/main/dags/clickhouse/load-igvf-logs.py'
)


@dag(
    schedule=CronDataIntervalTimetable(
        '0 6 * * *',
        timezone='America/Los_Angeles',
    ),
    start_date=datetime(2026, 5, 1, tzinfo=timezone("America/Los_Angeles")),
    catchup=False,
)
def load_igvf_logs_to_clickhouse():
    KubernetesPodOperator(
        task_id='load-igvf-logs-to-clickhouse',
        namespace='data-stack-dev',
        image='public.ecr.aws/cherry-lab/cherry-lab:clickhouse-loader-3.12.1',
        cmds=['bash', '-c'],
        arguments=[
            f'curl -fsSL {_SCRIPT_URL} | python - {{{{ ds }}}}'
        ],
        env_from=[
            V1EnvFromSource(
                secret_ref=V1SecretEnvSource(name='clickhouse-loader-aws-credentials'),
            ),
        ],
        env_vars=[
            V1EnvVar(
                name='CLICKHOUSE_PASSWORD',
                value_from=V1EnvVarSource(
                    secret_key_ref=V1SecretKeySelector(
                        name='clickhouse-password',
                        key='password',
                    ),
                ),
            ),
            V1EnvVar(
                name='CLICKHOUSE_HOST',
                value='clickhouse-clickhouse-headless',
            ),
        ],
        on_finish_action='delete_pod',
    )


load_igvf_logs_to_clickhouse()
