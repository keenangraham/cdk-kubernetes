from airflow.sdk import dag
from airflow.sdk import task

from datetime import datetime


@dag(
    schedule='@daily',
    start_date=datetime(2026, 5, 1),
    catchup=False,
)
def print_date():

    @task
    def print_logical_date(ds=None):
        print(f'Logical date: {ds}')

    print_logical_date()


print_date()

