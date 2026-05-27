import datetime
import logging
from airflow.operators.bash import BashOperator
from airflow.decorators import dag
from airflow.decorators import task

import pendulum


@dag(
    schedule=None,
    start_date=pendulum.datetime(2026, 5, 25, tz="America/Los_Angeles")
)
def test_dag():
    @task.bash
    def run_after_loop():
        return "echo hi && ls -l"

    run_after_loop()

test_dag()

logging.warning("Running DAG")
