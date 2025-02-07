import datetime

from airflow.models import DAG
from airflow.operators.bash import BashOperator

from airflow.utils.dates import days_ago


dag = DAG(
    dag_id="test dag",
    default_args={"owner": "me", "retries": 3, "start_date": days_ago(2)},
    schedule_interval=None,
    dagrun_timeout=datetime.timedelta(minutes=60),
)


run_this = BashOperator(task_id="run_after_loop", bash_command="echo hi && ls -l", dag=dag)


if __name__ == "__main__":
    dag.cli()
