from datetime import datetime, timedelta
from airflow import DAG
from airflow.sdk import Param
from airflow.sdk import BashOperator

PROJECT = '/opt/airflow/project'


def failure_callback(context):
    """Prints structured task/run/error context for diagnosis.

    Fires once per task after all retries are exhausted (default_args
    scope), satisfying Section 8.5/10.2's requirement to preserve enough
    context to diagnose a failure without digging through raw tracebacks.
    """
    ti = context['task_instance']
    print('=== TASK FAILED ===')
    print(f"dag_id={ti.dag_id}")
    print(f"run_id={context['run_id']}")
    print(f"task_id={ti.task_id}")
    print(f"try_number={ti.try_number}")
    print(f"execution_date={context.get('logical_date') or context.get('execution_date')}")
    print(f"exception={context.get('exception')}")


DEFAULT_ARGS = {
    'owner': 'dss150p',
    'retries': 2,
    'retry_delay': timedelta(minutes=2),
    'execution_timeout': timedelta(minutes=10),
    'on_failure_callback': failure_callback,
}

with DAG(
    dag_id='dss150p_sales_pipeline',
    start_date=datetime(2026, 1, 1),
    # Daily at 2 AM: after presumed midnight upstream exports land, and
    # comfortably before analysts start querying curated data during
    # business hours.
    schedule='0 2 * * *',
    # catchup=False: this pipeline reflects "current state of orders" via
    # rerun-safe upserts keyed on record_hash, not a strictly append-only
    # daily ledger. Automatically firing every missed historical schedule
    # on deploy/restart isn't meaningful here; a genuine backfill is a
    # deliberate, explicit action (see Section 10.6), not an automatic one.
    catchup=False,
    default_args=DEFAULT_ARGS,
    params={
        'run_mode': Param('full', enum=['full', 'partition']),
        'year': Param(2026, type='integer'),
        'month': Param(1, type='integer', minimum=1, maximum=12),
    },
    tags=['DSS150P'],
) as dag:
    extract = BashOperator(
        task_id='extract',
        bash_command=f'cd {PROJECT} && PIPELINE_RUN_ID="{{{{ run_id }}}}" python -m src.cli extract',
    )
    transform = BashOperator(
        task_id='transform',
        bash_command=f'cd {PROJECT} && PIPELINE_RUN_ID="{{{{ run_id }}}}" python -m src.cli transform',
    )
    load = BashOperator(
        task_id='load',
        bash_command=(
            f'cd {PROJECT} && PIPELINE_RUN_ID="{{{{ run_id }}}}" '
            '{% if params.run_mode == "partition" %}'
            'python -m src.cli load-partition --year {{ params.year }} --month {{ params.month }}'
            '{% else %}'
            'python -m src.cli load'
            '{% endif %}'
        ),
    )
    validate = BashOperator(
        task_id='validate',
        bash_command=f'cd {PROJECT} && PIPELINE_RUN_ID="{{{{ run_id }}}}" python -m src.cli validate',
    )

    extract >> transform >> load >> validate