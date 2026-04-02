"""
SkyOps Intelligence — Airflow 재학습 DAG
매일 00:00 UTC 에 실행되는 자동 재학습 파이프라인.

Pipeline:
  1. data_freshness_check  — 신규 데이터 존재 여부 확인
  2. build_alpaca_dataset  — alpaca jsonl 재빌드
  3. run_drift_detector    — EvidentlyAI 드리프트 감지
  4. retrain_qlora         — QLoRA 파인튜닝 (드리프트 감지 시만 실행)
  5. run_evaluation        — BLEU/ROUGE 평가
  6. slack_notify_results  — Slack Webhook 결과 알림

필수 Airflow Variables:
  SKYOPS_HOME       — 프로젝트 루트 절대경로
  SLACK_WEBHOOK_URL — Slack Incoming Webhook URL
  OPENAI_API_KEY    — (선택) GPT-4 QA 생성 시 사용

설치:
  1. python -m pip install apache-airflow
  2. 저장소 루트 밖의 디렉터리에서 Airflow 초기화
     - 이 저장소에는 top-level `airflow/` 폴더가 있어, repo root 에서
       `airflow` CLI 를 실행하면 Apache Airflow 패키지 import 와 충돌할 수 있다.
  3. Airflow CLI 예시 (PowerShell)
     - setx AIRFLOW_HOME C:\airflow
     - 새 터미널에서:
       - airflow db migrate
       - airflow variables set SKYOPS_HOME "C:\path\to\SkyOps Intelligence"
       - airflow variables set SLACK_WEBHOOK_URL "https://hooks.slack.com/..."
       - Copy-Item "C:\path\to\SkyOps Intelligence\airflow\dags\skyops_retrain_dag.py" "$env:AIRFLOW_HOME\dags\"
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.trigger_rule import TriggerRule

# ── 공통 설정 ──────────────────────────────────────────────────────────────────
DEFAULT_ARGS = {
    "owner":            "skyops",
    "depends_on_past":  False,
    "retries":          1,
    "retry_delay":      timedelta(minutes=5),
    "email_on_failure": False,
}

PYTHON = sys.executable   # Airflow 환경의 Python

# ── 헬퍼: SKYOPS_HOME 가져오기 ─────────────────────────────────────────────────
def get_home() -> str:
    return Variable.get("SKYOPS_HOME", default_var=str(Path(__file__).parent.parent.parent))


def run_script(script_rel: str, args: list[str] = (), env: dict | None = None) -> str:
    """프로젝트 스크립트를 서브프로세스로 실행한다."""
    home = get_home()
    cmd  = [PYTHON, str(Path(home) / script_rel)] + list(args)
    merged_env = {**os.environ, **(env or {})}

    print(f"[run] {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, env=merged_env)
    if result.stdout:
        print(result.stdout[-3000:])   # 마지막 3K chars
    if result.returncode != 0:
        raise RuntimeError(f"Script failed ({result.returncode}):\n{result.stderr[-2000:]}")
    return result.stdout


# ══════════════════════════════════════════════════════════════════════════════
# Task 함수
# ══════════════════════════════════════════════════════════════════════════════

def task_data_freshness_check(**ctx) -> str:
    """
    신규 Alpaca 데이터가 존재하는지 확인.
    XCom 에 'has_new_data' (bool) 저장.
    """
    home = Path(get_home())
    train_file = home / "data/alpaca/aviation_alpaca_train.jsonl"

    if not train_file.exists():
        print("[check] 학습 파일 없음 → 재빌드 필요")
        ctx["ti"].xcom_push(key="has_new_data", value=True)
        return

    mtime  = datetime.fromtimestamp(train_file.stat().st_mtime)
    age_h  = (datetime.now() - mtime).total_seconds() / 3600
    is_new = age_h < 25   # 25시간 이내 갱신 = 신규 데이터

    print(f"[check] {train_file.name} 최종 수정: {mtime}  ({age_h:.1f}h 전)")
    print(f"[check] has_new_data = {is_new}")
    ctx["ti"].xcom_push(key="has_new_data", value=is_new)


def task_build_alpaca(**ctx) -> None:
    """Alpaca 데이터셋 재빌드."""
    run_script("llm_data/build_alpaca_dataset.py")


def task_run_drift_detector(**ctx) -> str:
    """
    EvidentlyAI 드리프트 감지.
    결과를 XCom 에 저장하고 드리프트 여부 반환.
    """
    home = Path(get_home())
    report_path = home / "data/eval/drift_report.json"

    stdout = run_script(
        "monitoring/drift_detector.py",
        ["--output", str(report_path)],
    )

    # 드리프트 감지 스크립트가 JSON 마지막 줄로 결과 출력
    drift_detected = False
    try:
        if report_path.exists():
            with open(report_path) as f:
                report = json.load(f)
            drift_detected = report.get("drift_detected", False)
    except Exception as e:
        print(f"[drift] report 파싱 오류: {e}")

    print(f"[drift] drift_detected = {drift_detected}")
    ctx["ti"].xcom_push(key="drift_detected", value=drift_detected)


def task_branch_retrain(**ctx) -> str:
    """드리프트 감지 여부 + 신규 데이터 여부로 재학습 분기."""
    ti          = ctx["ti"]
    has_new     = ti.xcom_pull(task_ids="data_freshness_check", key="has_new_data") or False
    drift       = ti.xcom_pull(task_ids="run_drift_detector",   key="drift_detected") or False

    if has_new or drift:
        reason = []
        if has_new:
            reason.append("신규 데이터")
        if drift:
            reason.append("드리프트 감지")
        print(f"[branch] 재학습 필요: {', '.join(reason)}")
        return "retrain_qlora"
    else:
        print("[branch] 재학습 불필요 — 평가만 실행")
        return "skip_retrain"


def task_retrain_qlora(**ctx) -> None:
    """QLoRA 파인튜닝 재실행."""
    home = Path(get_home())
    run_script(
        "llm_data/fine_tune_qlora.py",
        [
            "--model",      "Qwen/Qwen2.5-7B-Instruct",
            "--dataset",    str(home / "data/alpaca/aviation_alpaca_train.jsonl"),
            "--output-dir", str(home / "data/models/llm/qwen25_7b_qlora"),
            "--epochs",     "1",
        ],
    )


def task_run_evaluation(**ctx) -> None:
    """
    재학습 후 벤치마크 평가.
    결과를 XCom 에 저장.
    """
    home = Path(get_home())
    bench_path  = home / "data/eval/benchmark_eval.jsonl"
    output_path = home / "data/eval/results_latest.json"

    # 벤치마크 없으면 먼저 생성
    if not bench_path.exists():
        run_script("evaluation/build_benchmark.py")

    adapter = home / "data/models/llm/qwen25_7b_qlora/final_adapter"
    if adapter.exists():
        run_script(
            "evaluation/evaluate_model.py",
            [
                "--model",      str(adapter),
                "--base-model", "Qwen/Qwen2.5-7B-Instruct",
                "--benchmark",  str(bench_path),
                "--output",     str(output_path),
                "--tag",        "AviationLLM-Daily",
            ],
        )
    else:
        # 어댑터 없으면 오프라인 스코어만 계산
        run_script(
            "evaluation/evaluate_model.py",
            ["--offline", "--output", str(output_path), "--tag", "Offline"],
        )

    if output_path.exists():
        with open(output_path) as f:
            result = json.load(f)
        summary = result.get("summary", {})
        ctx["ti"].xcom_push(key="eval_summary", value=summary)
        print(f"[eval] BLEU-4={summary.get('bleu_4','?')}  ROUGE-L={summary.get('rouge_l','?')}")


def task_slack_notify(**ctx) -> None:
    """Slack Webhook 으로 결과 알림."""
    home = Path(get_home())
    ti   = ctx["ti"]

    eval_summary   = ti.xcom_pull(task_ids="run_evaluation",    key="eval_summary") or {}
    drift_detected = ti.xcom_pull(task_ids="run_drift_detector", key="drift_detected") or False
    has_new_data   = ti.xcom_pull(task_ids="data_freshness_check", key="has_new_data") or False

    run_script(
        "monitoring/slack_notifier.py",
        [
            "--bleu4",     str(eval_summary.get("bleu_4",  "N/A")),
            "--rouge-l",   str(eval_summary.get("rouge_l", "N/A")),
            "--drift",     str(drift_detected).lower(),
            "--new-data",  str(has_new_data).lower(),
            "--dag-run",   ctx["run_id"],
        ],
    )


# ══════════════════════════════════════════════════════════════════════════════
# DAG 정의
# ══════════════════════════════════════════════════════════════════════════════
with DAG(
    dag_id          = "skyops_daily_retrain",
    default_args    = DEFAULT_ARGS,
    description     = "SkyOps Intelligence 일별 자동 재학습 + 평가 + 알림",
    schedule_interval = "0 0 * * *",   # 매일 00:00 UTC
    start_date      = datetime(2026, 4, 1),
    catchup         = False,
    tags            = ["skyops", "llm", "retrain"],
    max_active_runs = 1,
) as dag:

    t_check = PythonOperator(
        task_id         = "data_freshness_check",
        python_callable = task_data_freshness_check,
        provide_context = True,
    )

    t_build = PythonOperator(
        task_id         = "build_alpaca_dataset",
        python_callable = task_build_alpaca,
        provide_context = True,
    )

    t_drift = PythonOperator(
        task_id         = "run_drift_detector",
        python_callable = task_run_drift_detector,
        provide_context = True,
    )

    t_branch = BranchPythonOperator(
        task_id         = "branch_retrain_decision",
        python_callable = task_branch_retrain,
        provide_context = True,
    )

    t_retrain = PythonOperator(
        task_id         = "retrain_qlora",
        python_callable = task_retrain_qlora,
        provide_context = True,
    )

    t_skip = EmptyOperator(task_id="skip_retrain")

    t_eval = PythonOperator(
        task_id         = "run_evaluation",
        python_callable = task_run_evaluation,
        provide_context = True,
        trigger_rule    = TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )

    t_notify = PythonOperator(
        task_id         = "slack_notify_results",
        python_callable = task_slack_notify,
        provide_context = True,
        trigger_rule    = TriggerRule.ALL_DONE,
    )

    # ── 의존관계 ──────────────────────────────────────────────────────────────
    t_check >> t_build >> t_drift >> t_branch
    t_branch >> [t_retrain, t_skip]
    [t_retrain, t_skip] >> t_eval >> t_notify
