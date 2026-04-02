"""
SkyOps Intelligence — Slack Webhook 알림 모듈
학습 결과, 드리프트 감지, 에러 발생 시 Slack 채널에 메시지를 전송한다.

환경변수:
    SLACK_WEBHOOK_URL — Slack Incoming Webhook URL
                        (Airflow Variable 또는 .env 에 설정)

Usage:
    # 단독 실행
    python monitoring/slack_notifier.py \
        --bleu4 0.423 --rouge-l 0.518 \
        --drift true --new-data false \
        --dag-run manual_2026_04_02

    # 모듈로 임포트
    from monitoring.slack_notifier import notify_train_result, notify_drift, notify_error
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


# ── Webhook 전송 ──────────────────────────────────────────────────────────────
def _post(webhook_url: str, payload: dict) -> bool:
    """urllib 으로 Slack API 호출 (requests 의존성 없이 동작)."""
    import urllib.request, urllib.error

    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        webhook_url,
        data    = data,
        headers = {"Content-Type": "application/json"},
        method  = "POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode()
            if body == "ok":
                print("[slack] 전송 성공")
                return True
            else:
                print(f"[slack] 응답: {body}")
                return False
    except urllib.error.HTTPError as e:
        print(f"[slack] HTTP 오류 {e.code}: {e.read().decode()}")
        return False
    except Exception as e:
        print(f"[slack] 전송 실패: {e}")
        return False


def _get_webhook() -> str | None:
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        # Airflow Variable fallback
        try:
            from airflow.models import Variable
            url = Variable.get("SLACK_WEBHOOK_URL", default_var=None)
        except Exception:
            pass
    if not url:
        # .env 파일 fallback
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("SLACK_WEBHOOK_URL="):
                    url = line.split("=", 1)[1].strip().strip('"').strip("'")
    return url


# ── 메시지 빌더 ────────────────────────────────────────────────────────────────
def _status_emoji(val: float | None, good_threshold: float = 0.3) -> str:
    if val is None:
        return "❓"
    return "✅" if val >= good_threshold else "⚠️"


def build_train_result_message(
    bleu4: float | None,
    rouge_l: float | None,
    drift_detected: bool,
    new_data: bool,
    dag_run: str = "",
    train_loss: float | None = None,
    eval_loss: float | None = None,
) -> dict:
    ts    = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    title = "🛫 *SkyOps Intelligence* — 일별 재학습 완료" if (new_data or drift_detected) else \
            "🛫 *SkyOps Intelligence* — 정기 평가 완료"

    bleu4_str  = f"{bleu4:.4f}"  if bleu4  is not None else "N/A"
    rouge_str  = f"{rouge_l:.4f}" if rouge_l is not None else "N/A"
    b4_emoji   = _status_emoji(bleu4, 0.3)
    rl_emoji   = _status_emoji(rouge_l, 0.4)

    blocks = [
        {"type": "header",
         "text": {"type": "plain_text", "text": "SkyOps Intelligence — 재학습 리포트"}},
        {"type": "section",
         "text": {"type": "mrkdwn",
                  "text": f"*{title}*\n_{ts}_"}},
        {"type": "divider"},
        {"type": "section",
         "fields": [
             {"type": "mrkdwn", "text": f"*{b4_emoji} BLEU-4*\n`{bleu4_str}`"},
             {"type": "mrkdwn", "text": f"*{rl_emoji} ROUGE-L*\n`{rouge_str}`"},
         ]},
    ]

    if train_loss is not None or eval_loss is not None:
        blocks.append({
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Train Loss*\n`{train_loss:.4f}`" if train_loss else "*Train Loss*\nN/A"},
                {"type": "mrkdwn", "text": f"*Eval Loss*\n`{eval_loss:.4f}`"  if eval_loss  else "*Eval Loss*\nN/A"},
            ],
        })

    trigger_parts = []
    if new_data:        trigger_parts.append("📥 신규 데이터")
    if drift_detected:  trigger_parts.append("⚠️ 드리프트 감지")
    if not trigger_parts: trigger_parts.append("⏰ 정기 스케줄")

    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn",
             "text": f"트리거: {' + '.join(trigger_parts)}   |   DAG Run: `{dag_run}`"}
        ],
    })

    return {"blocks": blocks}


def build_drift_alert_message(signals: list[str], details: dict) -> dict:
    sig_text = "\n".join(f"• {s}" for s in signals) if signals else "• 세부 신호 없음"
    return {
        "blocks": [
            {"type": "header",
             "text": {"type": "plain_text", "text": "⚠️ SkyOps — 데이터 드리프트 감지"}},
            {"type": "section",
             "text": {"type": "mrkdwn",
                      "text": f"*드리프트 신호:*\n{sig_text}"}},
            {"type": "section",
             "fields": [
                 {"type": "mrkdwn", "text": f"*JSD*\n`{details.get('keyword_jsd', 'N/A')}`"},
                 {"type": "mrkdwn", "text": f"*길이 Z*\n`{details.get('len_z_score', 'N/A')}`"},
             ]},
            {"type": "context",
             "elements": [{"type": "mrkdwn",
                           "text": f"자동 재학습이 트리거됩니다.  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"}]},
        ]
    }


def build_error_message(task: str, error: str, dag_run: str = "") -> dict:
    return {
        "blocks": [
            {"type": "header",
             "text": {"type": "plain_text", "text": "🚨 SkyOps — 파이프라인 오류"}},
            {"type": "section",
             "text": {"type": "mrkdwn",
                      "text": f"*태스크:* `{task}`\n*오류:*\n```{error[:500]}```"}},
            {"type": "context",
             "elements": [{"type": "mrkdwn",
                           "text": f"DAG Run: `{dag_run}`  |  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"}]},
        ]
    }


# ── 공개 함수 ──────────────────────────────────────────────────────────────────
def notify_train_result(bleu4=None, rouge_l=None, drift_detected=False,
                        new_data=False, dag_run="", **kwargs) -> bool:
    url = _get_webhook()
    if not url:
        print("[slack] SLACK_WEBHOOK_URL 미설정 — 알림 생략")
        return False
    payload = build_train_result_message(bleu4, rouge_l, drift_detected, new_data, dag_run, **kwargs)
    return _post(url, payload)


def notify_drift(signals: list[str], details: dict) -> bool:
    url = _get_webhook()
    if not url:
        print("[slack] SLACK_WEBHOOK_URL 미설정 — 알림 생략")
        return False
    payload = build_drift_alert_message(signals, details)
    return _post(url, payload)


def notify_error(task: str, error: str, dag_run: str = "") -> bool:
    url = _get_webhook()
    if not url:
        print("[slack] SLACK_WEBHOOK_URL 미설정 — 알림 생략")
        return False
    payload = build_error_message(task, error, dag_run)
    return _post(url, payload)


# ── CLI ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bleu4",     default=None, type=float)
    parser.add_argument("--rouge-l",   default=None, type=float)
    parser.add_argument("--drift",     default="false")
    parser.add_argument("--new-data",  default="false")
    parser.add_argument("--dag-run",   default="manual")
    parser.add_argument("--train-loss",type=float, default=None)
    parser.add_argument("--eval-loss", type=float, default=None)
    parser.add_argument("--dry-run",   action="store_true",
                        help="Webhook 전송 없이 payload 만 출력")
    args = parser.parse_args()

    drift    = args.drift.lower()    in ("true", "1", "yes")
    new_data = args.new_data.lower() in ("true", "1", "yes")

    payload = build_train_result_message(
        bleu4          = args.bleu4,
        rouge_l        = getattr(args, "rouge_l"),
        drift_detected = drift,
        new_data       = new_data,
        dag_run        = args.dag_run,
        train_loss     = args.train_loss,
        eval_loss      = args.eval_loss,
    )

    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    url = _get_webhook()
    if not url:
        print("[slack] SLACK_WEBHOOK_URL 미설정")
        print("[slack] dry-run payload:")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    _post(url, payload)


if __name__ == "__main__":
    main()
