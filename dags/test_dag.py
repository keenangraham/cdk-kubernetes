import datetime
import logging
from airflow.operators.bash import BashOperator
from airflow.decorators import dag
from airflow.decorators import task

import pendulum


@dag(
    schedule=None,
    start_date=pendulum.now('UTC').subtract(days=2)
)
def test_dag():
    @task.bash
    def run_after_loop():
        return "echo hi && ls -l"

    run_after_loop()

test_dag()

logging.warning("Running DAG")
