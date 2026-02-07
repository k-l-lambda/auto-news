from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email': [''],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
        'health_check',
        default_args=default_args,
        max_active_runs=1,
        description='Health check for auto-news pipeline. Detects and auto-fixes '
                    'issues like Notion schema overflow.',
        schedule_interval="30 */6 * * *",  # Every 6 hours at minute 30
        start_date=days_ago(0),
        tags=['NewsBot', 'Health'],
        catchup=False,
) as dag:

    t1 = BashOperator(
        task_id='health_check',
        bash_command='cd ~/airflow/run/auto-news/src && python3 health_check.py '
                     '--log-dir=/opt/airflow/logs '
                     '--hours=6 ',
    )

    t1
