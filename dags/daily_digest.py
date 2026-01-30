from datetime import datetime, timedelta

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG

# Operators; we need this to operate!
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

# These args will get passed on to each operator
# You can override them on a per-task basis during operator initialization
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email': [''],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


with DAG(
    'daily_digest',
    default_args=default_args,
    max_active_runs=1,
    description='Daily news digest from ToRead items. Config: {"sources": "Article,RSS,Twitter,Reddit,Youtube,Web", "targets": "notion", "hours_back": 24, "min_rating": 3}',
    # Schedule at 22:00 UTC = 6:00 AM SGT (UTC+8)
    # Note: Actual timezone is configurable via DAILY_DIGEST_TIMEZONE env var
    schedule_interval="0 22 * * *",
    start_date=days_ago(1),
    tags=['NewsBot', 'DailyDigest'],
) as dag:

    t1 = BashOperator(
        task_id='start',
        bash_command='cd ~/airflow/run/auto-news/src && python3 af_start.py --start {{ ds }} --prefix=./run',
    )

    t2 = BashOperator(
        task_id='prepare',
        bash_command='mkdir -p ~/airflow/data/daily_digest/{{ run_id }}',
    )

    t3 = BashOperator(
        task_id='pull',
        bash_command='cd ~/airflow/run/auto-news/src && python3 af_daily_digest_pull.py '
        '--start {{ ds }} '
        '--prefix=./run '
        '--run-id={{ run_id }} '
        '--job-id={{ ti.job_id }} '
        '--data-folder=data/daily_digest '
        '--sources={{ dag_run.conf.setdefault("sources", "Article,RSS,Twitter,Reddit,Youtube,Web") }} '
        '--hours-back={{ dag_run.conf.setdefault("hours_back", 24) }} '
        '--min-rating={{ dag_run.conf.setdefault("min_rating", 3) }} '
    )

    t4 = BashOperator(
        task_id='generate_and_push',
        bash_command='cd ~/airflow/run/auto-news/src && python3 af_daily_digest_save.py '
        '--start {{ ds }} '
        '--prefix=./run '
        '--run-id={{ run_id }} '
        '--job-id={{ ti.job_id }} '
        '--data-folder=data/daily_digest '
        '--targets={{ dag_run.conf.setdefault("targets", "notion") }} '
    )

    t5 = BashOperator(
        task_id='finish',
        depends_on_past=False,
        bash_command='cd ~/airflow/run/auto-news/src && python3 af_end.py '
        '--start {{ ds }} '
        '--prefix=./run ',
    )

    t1 >> t2 >> t3 >> t4 >> t5
