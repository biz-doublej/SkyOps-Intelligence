"""Airflow DAG — SkyOps Active Learning Loop (P6-C · 2026-04-15).

Daily cadence:
  02:00 UTC  →  run active_learning_retrain (dry-run)
  02:30 UTC  →  if decisions indicate retrain, run full retrain
  03:00 UTC  →  touch reload signal so serving picks up new IF

Schedule:
  schedule_interval = @daily
  start_date = 2026-04-15

Manual trigger:
  airflow dags trigger skyops_active_learning
"""
from __future__ import annotations

import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_ROOT = "/opt/skyops"  # set in docker-compose or via AIRFLOW__CORE__DAGS_FOLDER

default_args = {
    "owner": "skyops-ml-team",
    "retries": 1,
    "retry_delay": pendulum.duration(minutes=15),
}

with DAG(
    dag_id="skyops_active_learning",
    description="Active learning retrain loop (feedback → contamination tune → IF retrain → hot reload)",
    schedule="0 2 * * *",
    start_date=pendulum.datetime(2026, 4, 15, tz="UTC"),
    catchup=False,
    tags=["skyops", "active-learning", "ml-ops"],
    default_args=default_args,
) as dag:

    analyze_feedback = BashOperator(
        task_id="analyze_feedback",
        bash_command=(
            f"cd {PROJECT_ROOT} && "
            f"PYTHONIOENCODING=utf-8 python -m analysis.active_learning"
        ),
    )

    dry_run_retrain = BashOperator(
        task_id="dry_run_retrain",
        bash_command=(
            f"cd {PROJECT_ROOT} && "
            f"PYTHONIOENCODING=utf-8 python -m analysis.active_learning_retrain --dry-run"
        ),
    )

    retrain_if_needed = BashOperator(
        task_id="retrain_if_needed",
        bash_command=(
            f"cd {PROJECT_ROOT} && "
            # only actually retrain if contamination_adjusted.json has any delta
            f"python -c \""
            f"import json,sys,pathlib;"
            f"d=json.loads(pathlib.Path('data/models/contamination_adjusted.json').read_text());"
            f"changes=[k for k,v in d['decisions'].items() if abs(v.get('delta',0))>1e-6];"
            f"print('phases_changed:', changes);"
            f"sys.exit(0 if changes else 99)\" && "
            f"PYTHONIOENCODING=utf-8 python -m analysis.active_learning_retrain"
        ),
    )

    analyze_feedback >> dry_run_retrain >> retrain_if_needed
