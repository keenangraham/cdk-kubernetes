import datetime

from airflow.models.dag import DAG
from airflow.providers.standard.operators.bash import BashOperator


dag = DAG(
    dag_id="test dag",
    default_args={"owner": "airflow", "retries": 3, "start_date": datetime.datetime(2022, 1, 1)},
    schedule_interval=None,
    dagrun_timeout=datetime.timedelta(minutes=60),
)


run_this = BashOperator(task_id="run_after_loop", bash_command="echo hi && ls -l", dag=dag)
