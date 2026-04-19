"""Anomaly detection router — /detect/anomaly, /anomaly/feedback.

ADR-001 Migration Phase 1 (2026-04-14 P3).
P2 Phase-aware detection + Redis debounce + Analyst feedback stub.
"""

from __future__ import annotations

import json as _json
import math
import time
from datetime import datetime, timezone

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from common.auth import (
    Principal,
    get_principal,
    require_analyst,
)

from common.constants import (
    FEEDBACK_DIR,
    FEEDBACK_FILE,
    IF_FEATURES,
    IF_HYSTERESIS_TTL_SEC,
    IF_SCORE_ENTER,
    IF_SCORE_EXIT,
    IF_SCORE_THRESHOLD,
    REDIS_AIRCRAFT_PHASE,
    REDIS_ANOMALY_DEBOUNCE,
    REDIS_ANOMALY_HYSTERESIS,
    REDIS_ANOMALY_STREAM,
    REDIS_ANOMALY_SUPPRESS_AUDIT,
)
from common.model_store import ModelStore
from common.suppression import SUPPRESSION_ENABLED, SuppressionEngine
from common.models import (
    ActiveLearningItem,
    ActiveLearningQuery,
    AnomalyApprovalRequest,
    AnomalyApprovalResponse,
    AnomalyFeedbackRequest,
    AnomalyFeedbackResponse,
    AnomalyRequest,
    AnomalyResponse,
)
# v2.2.0 · ADR-007 D2 — TriageItem/TriageResponse + /alerts/triage 는
# serving/routers/alert_triage.py 로 이관됨. anomaly.py 는 detection /
# feedback / approve 만 담당.
from common.redis_client import get_redis
from common.telemetry import get_tracer

router = APIRouter(tags=["anomaly"])
tracer = get_tracer("anomaly")


# ──────────────────────────────────────────────────────────────────────
# v2.1.10 · ADR-006 · Phase-aware routing + hysteresis + suppression
# ──────────────────────────────────────────────────────────────────────

def _resolve_phase(req: AnomalyRequest, r) -> tuple[str | None, float | None]:
    """Pick the flight phase to route on.

    Priority:
      1. Explicit req.flight_phase (if caller knows it).
      2. Redis `skyops:aircraft:phase:{flight_id}` hash from live ADS-B classifier.
      3. None → base model fallback in ModelStore.
    """
    if req.flight_phase:
        return req.flight_phase.upper(), 1.0
    if req.flight_id and r is not None:
        try:
            phase_data = r.hgetall(REDIS_AIRCRAFT_PHASE.format(req.flight_id))
            if phase_data:
                phase = phase_data.get("phase")
                conf_str = phase_data.get("confidence")
                return (
                    phase.upper() if phase else None,
                    float(conf_str) if conf_str else None,
                )
        except Exception:
            pass
    return None, None


def _apply_hysteresis(flight_id: str | None, score: float, r) -> tuple[bool, str]:
    """Enter/exit hysteresis state machine.

    Returns (is_alerting, new_state).  new_state in {"clear", "alerting"}.

    - `score < IF_SCORE_ENTER`  → alerting
    - `score > IF_SCORE_EXIT`   → clear
    - otherwise → keep previous state (flapping 방지)

    State is persisted in Redis with TTL (default 15 min). Missing state =
    treated as "clear" (cold start).
    """
    if r is None or not flight_id:
        # Redis 없으면 단일 임계값 fallback.
        return score < IF_SCORE_ENTER, ("alerting" if score < IF_SCORE_ENTER else "clear")

    key = REDIS_ANOMALY_HYSTERESIS.format(flight_id)
    try:
        prev = r.get(key) or "clear"
    except Exception:
        prev = "clear"

    if score < IF_SCORE_ENTER:
        new_state = "alerting"
    elif score > IF_SCORE_EXIT:
        new_state = "clear"
    else:
        new_state = prev  # hysteresis band → 현상 유지

    if new_state != prev:
        try:
            r.setex(key, IF_HYSTERESIS_TTL_SEC, new_state)
        except Exception:
            pass
    else:
        try:
            # TTL 갱신 (활성 flight 은 state 유지)
            r.expire(key, IF_HYSTERESIS_TTL_SEC)
        except Exception:
            pass
    return new_state == "alerting", new_state


def _check_suppression(req: AnomalyRequest, phase: str | None, r) -> tuple[bool, str | None, str | None]:
    """Check alert_suppression.yaml rules. Returns (suppressed, reason, kind)."""
    if not SUPPRESSION_ENABLED:
        return False, None, None
    try:
        engine = SuppressionEngine.singleton()
    except Exception as e:  # noqa: BLE001
        print(f"⚠️  suppression engine 초기화 실패: {e}")
        return False, None, None

    # 출발·도착 공항, icao24 중 하나라도 매칭되면 suppress.
    for airport in (req.origin, req.dest):
        sup, reason, kind = engine.matches(airport=airport, icao24=req.icao24)
        if sup:
            # Audit log to Redis Stream (best-effort).
            if r is not None:
                try:
                    r.xadd(REDIS_ANOMALY_SUPPRESS_AUDIT, {
                        "flight_id": req.flight_id or "",
                        "icao24": req.icao24 or "",
                        "airport": airport or "",
                        "phase": phase or "",
                        "reason": reason or "",
                        "kind": kind or "",
                        "ts": datetime.now(timezone.utc).isoformat(),
                    }, maxlen=10000, approximate=True)
                except Exception:
                    pass
            return True, reason, kind
    return False, None, None


@router.post("/detect/anomaly", response_model=AnomalyResponse)
def detect_anomaly(req: AnomalyRequest) -> AnomalyResponse:
    """Isolation Forest 이상 탐지 — phase-aware + hysteresis + suppression + debounce.

    Alert discipline 파이프라인 (v2.1.10 · ADR-006):
      1. Resolve flight phase (explicit req / Redis / none)
      2. Suppression check (maintenance / weather / airport closure)
         → 매칭 시 is_anomaly=False, suppressed=true, audit log
      3. Route to per-phase IF model (7개 중 하나, 없으면 base fallback)
      4. Compute score / pred
      5. Hysteresis state machine (enter=-0.15, exit=-0.05)
      6. Debounce (same flight 60 s, critical 제외)
      7. Final AnomalyResponse — alert_state/model_source 추가
    """
    t0 = time.time()
    r = get_redis()

    with tracer.start_as_current_span("if_inference") as span:
        # ── (1) Phase 결정 ────────────────────────────────────────
        phase, phase_confidence = _resolve_phase(req, r)
        if phase:
            span.set_attribute("flight_phase", phase)

        # ── (2) Suppression 체크 (모델 호출 전 short-circuit) ─────
        sup_suppressed, sup_reason, sup_kind = _check_suppression(req, phase, r)
        if sup_suppressed:
            span.set_attribute("suppressed", True)
            span.set_attribute("suppress_kind", sup_kind or "")
            latency = (time.time() - t0) * 1000
            return AnomalyResponse(
                flight_id=req.flight_id,
                anomaly_score=0.0,
                is_anomaly=False,
                risk_level="normal",
                latency_ms=round(latency, 1),
                flight_phase=phase,
                phase_confidence=phase_confidence,
                suppressed=True,
                suppress_reason=f"{sup_kind}:{sup_reason}" if sup_kind else sup_reason,
                alert_state="clear",
                model_source=None,
            )

        # ── (3) Per-phase 모델 라우팅 ─────────────────────────────
        try:
            model, resolved_phase, model_source = ModelStore.isolation_forest_for_phase(phase)
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e))
        span.set_attribute("model_source", model_source)

        # ── (4) Inference ────────────────────────────────────────
        row = {f: getattr(req, f) for f in IF_FEATURES}
        X = pd.DataFrame([row])[IF_FEATURES]
        try:
            score = float(model.decision_function(X)[0])
            pred = int(model.predict(X)[0])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"이상 탐지 오류: {e}")
        span.set_attribute("anomaly_score", score)

        # ── (5) Hysteresis state machine ─────────────────────────
        is_alerting, alert_state = _apply_hysteresis(req.flight_id, score, r)
        # 모델의 raw 예측도 고려 — IF 가 강하게 -1 을 주면 alerting 강제.
        is_anomaly = is_alerting or (pred == -1 and score < IF_SCORE_ENTER)
        span.set_attribute("alert_state", alert_state)

        # risk_level — hysteresis 반영
        if score < -0.2:
            risk_level = "critical"
        elif is_alerting:
            risk_level = "warning"
        else:
            risk_level = "normal"

        # ── (6) Debounce (기존 로직 유지) ─────────────────────────
        suppressed = False
        suppress_reason = None
        if is_anomaly and risk_level != "critical" and req.flight_id and r is not None:
            dkey = REDIS_ANOMALY_DEBOUNCE.format(req.flight_id, "IF_DETECT")
            try:
                if r.exists(dkey):
                    suppressed = True
                    suppress_reason = "debounce_60s_same_flight"
                else:
                    r.setex(dkey, 60, "1")
            except Exception:
                pass

        if suppressed:
            span.set_attribute("suppressed", True)

    latency = (time.time() - t0) * 1000
    return AnomalyResponse(
        flight_id=req.flight_id,
        anomaly_score=round(score, 4),
        is_anomaly=is_anomaly,
        risk_level=risk_level,
        latency_ms=round(latency, 1),
        flight_phase=phase,
        phase_confidence=phase_confidence,
        suppressed=suppressed,
        suppress_reason=suppress_reason,
        alert_state=alert_state,
        model_source=model_source,
    )


@router.post(
    "/anomaly/feedback",
    response_model=AnomalyFeedbackResponse,
    dependencies=[Depends(require_analyst)],  # v2.2.0 · ADR-007 D4a RBAC
)
def submit_anomaly_feedback(
    req: AnomalyFeedbackRequest,
    principal: Principal = Depends(get_principal),
) -> AnomalyFeedbackResponse:
    """Analyst feedback → data/analyst_feedback/feedback.jsonl.

    RBAC: analyst 또는 admin 역할 필요. v2.2.0 부터 req.labeled_by 가
    principal.user 로 강제 overwrite 됨 (header spoofing 방지).
    """
    # v2.2.0 · 신뢰 가능한 identity 로 labeled_by 강제 설정 (클라이언트 제공값 무시)
    if principal.authenticated:
        req.labeled_by = principal.user
    valid_labels = {"true_positive", "false_positive", "uncertain"}
    if req.label not in valid_labels:
        raise HTTPException(
            status_code=400,
            detail=f"label은 {valid_labels} 중 하나여야 합니다.",
        )

    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "alert_id": req.alert_id,
        "label": req.label,
        "note": req.note,
        "labeled_by": req.labeled_by,
        "labeled_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
            f.write(_json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"피드백 저장 실패: {e}")

    # P8-A: Gold anomaly_decisions Iceberg write + audit log
    try:
        from feature_store.iceberg_writer import write_gold_anomaly_decision  # type: ignore
        write_gold_anomaly_decision(
            alert_id=req.alert_id,
            anomaly_type="unknown_from_feedback",
            severity="unknown",
            flight_phase=None,
            analyst_label=req.label,
        )
    except Exception:
        pass

    # P8-F: structured audit log
    try:
        from common.audit import audit_log  # type: ignore
        audit_log(event="anomaly_feedback_submitted",
                  actor=req.labeled_by, resource=req.alert_id, outcome="saved",
                  extra={"label": req.label})
    except Exception:
        pass

    return AnomalyFeedbackResponse(
        saved=True,
        alert_id=req.alert_id,
        file_path=str(FEEDBACK_FILE),
    )


# ──────────────────────────────────────────────────────────────────────
# GET /active-learning/next — Uncertainty sampling queue (P4+ · 2026-04-15)
# ──────────────────────────────────────────────────────────────────────

def _load_labeled_alert_ids() -> set[str]:
    """이미 라벨된 alert_id를 feedback.jsonl에서 로드."""
    if not FEEDBACK_FILE.exists():
        return set()
    labeled: set[str] = set()
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = _json.loads(line)
                    if rec.get("alert_id"):
                        labeled.add(rec["alert_id"])
                except _json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return labeled


def _uncertainty_score(
    anomaly_score: float,
    severity: str,
    threshold: float = IF_SCORE_THRESHOLD,
) -> float:
    """Uncertainty sampling: threshold에 가까울수록 1에 가까움.

    - decision_function threshold 근처 (|score - threshold| 작을수록 불확실)
    - HIGH severity는 확실 (label 명확) → uncertainty 낮춤
    - LOW/MEDIUM severity는 uncertainty 높임
    """
    # Distance to threshold (threshold는 음수, score도 음수 possible)
    distance = abs(anomaly_score - threshold)
    # exponential decay: 거리 0 → 1.0, 거리 멀수록 0
    base = float(math.exp(-distance * 5))  # 5x scale

    # Severity modifier
    sev = severity.upper() if severity else "LOW"
    if sev == "HIGH" or sev == "CRITICAL":
        base *= 0.3  # HIGH는 보통 확실 → label 우선순위 낮음
    elif sev == "LOW":
        base *= 1.2  # LOW는 더 불확실 → 우선순위 높음
    # MEDIUM = 1.0

    return float(min(1.0, max(0.0, base)))


@router.get("/active-learning/next", response_model=ActiveLearningQuery)
def get_next_items_for_labeling(top_k: int = 10, strategy: str = "uncertainty_v1"):
    """분석가 라벨링 우선순위 queue.

    strategy = "uncertainty_v1" (default, P4+):
      uncertainty_score = f(|anomaly_score - threshold|, severity)
      → top-K by uncertainty descending

    strategy = "bandit_v2" (P7-C, Thompson sampling + diversity):
      per anomaly_type bucket, sample exploitation reward from Beta(α,β)
      where α = 1 + true_positives, β = 1 + false_positives in feedback.
      Then ε-greedy diversify across phases so analyst doesn't get
      8 items all from CRUISE.

      Goal: balance "label what we're unsure about" vs "label types we
      haven't seen enough of yet".
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    labeled = _load_labeled_alert_ids()

    r = get_redis()
    if r is None:
        return ActiveLearningQuery(
            items=[],
            total_pending=0,
            returned_count=0,
            query_strategy="uncertainty_sampling_v1",
            generated_at=generated_at,
        )

    try:
        # 최근 500건 스트림 조회
        raw_events = r.lrange(REDIS_ANOMALY_STREAM, 0, 499)
    except Exception as e:
        print(f"⚠️  active-learning Redis 조회 실패: {e}")
        return ActiveLearningQuery(
            items=[],
            total_pending=0,
            returned_count=0,
            query_strategy="uncertainty_sampling_v1",
            generated_at=generated_at,
        )

    items: list[ActiveLearningItem] = []
    total_pending = 0
    for raw in raw_events:
        try:
            evt = _json.loads(raw)
        except _json.JSONDecodeError:
            continue
        alert_id = evt.get("alert_id", "")
        if not alert_id or alert_id in labeled:
            continue  # 이미 라벨됨 skip

        total_pending += 1

        # AnomalyEvent in pipeline/cep_rules.py stores `anomaly_score` / `severity` / `anomaly_type`
        # Some older events may lack fields; fallback 안전
        score = float(evt.get("anomaly_score", -0.15) or -0.15)
        severity = evt.get("severity", "LOW")
        uncertainty = _uncertainty_score(score, severity)

        items.append(ActiveLearningItem(
            alert_id=alert_id,
            anomaly_score=score,
            anomaly_type=evt.get("anomaly_type", "UNKNOWN"),
            severity=severity,
            flight_phase=evt.get("flight_phase"),
            icao24=evt.get("icao24"),
            callsign=evt.get("callsign"),
            description=evt.get("description", "")[:300],
            uncertainty_score=uncertainty,
        ))

    # ── Strategy dispatch ───────────────────────────────────────────
    if strategy == "bandit_v2":
        top = _bandit_v2_select(items, top_k=top_k, labeled_records=_load_labeled_records())
        strat_name = "bandit_v2_thompson_diversity"
    else:
        # default: uncertainty v1
        items.sort(key=lambda x: x.uncertainty_score, reverse=True)
        top = items[:max(1, top_k)]
        strat_name = "uncertainty_sampling_v1"

    return ActiveLearningQuery(
        items=top,
        total_pending=total_pending,
        returned_count=len(top),
        query_strategy=strat_name,
        generated_at=generated_at,
    )


# ── P7-C · Bandit v2 helpers ──────────────────────────────────────────
def _load_labeled_records() -> list[dict]:
    """Read full feedback.jsonl rows (not just IDs) for bandit prior."""
    if not FEEDBACK_FILE.exists():
        return []
    out: list[dict] = []
    try:
        for line in FEEDBACK_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(_json.loads(line))
            except Exception:
                continue
    except Exception:
        pass
    return out


def _thompson_sample(alpha: float, beta: float) -> float:
    """Sample from Beta(α, β) — Thompson posterior sample for TP probability.

    Higher = expected to be a true positive; lower = likely FP.
    For active learning, we want HIGH expected uncertainty AND
    types where we're uncertain of the TP rate.
    """
    import random
    # Beta sampling via gamma quotient (avoids numpy dependency in serving hot path)
    x = random.gammavariate(max(alpha, 1e-6), 1.0)
    y = random.gammavariate(max(beta, 1e-6), 1.0)
    return x / (x + y) if (x + y) > 0 else 0.5


def _bandit_v2_select(items: list[ActiveLearningItem],
                       top_k: int,
                       labeled_records: list[dict]) -> list[ActiveLearningItem]:
    """Bandit + diversity pick.

    Algorithm:
      1. Group candidates by anomaly_type
      2. For each type, compute Beta(1+TP, 1+FP) from labeled feedback,
         then Thompson sample → posterior_uncertainty = 1 - |0.5 - sample|*2
      3. Composite score = uncertainty_score * posterior_uncertainty
      4. Round-robin across (type, phase) buckets to enforce diversity
    """
    from collections import defaultdict

    # Per-type TP/FP counts from feedback (assumes feedback row has anomaly_type)
    counts: dict[str, dict] = defaultdict(lambda: {"tp": 0, "fp": 0})
    for r in labeled_records:
        atype = r.get("anomaly_type") or "UNKNOWN"
        label = (r.get("label") or "").lower()
        if label == "true_positive":
            counts[atype]["tp"] += 1
        elif label == "false_positive":
            counts[atype]["fp"] += 1

    # Composite score
    for it in items:
        c = counts.get(it.anomaly_type, {"tp": 0, "fp": 0})
        sample = _thompson_sample(1 + c["tp"], 1 + c["fp"])
        # Closer to 0.5 → more uncertain about TP rate → higher pick weight
        posterior_uncertainty = 1.0 - abs(sample - 0.5) * 2.0
        it.uncertainty_score = float(min(1.0,
            it.uncertainty_score * 0.6 + posterior_uncertainty * 0.4))

    # Group by (type, phase) for diversification
    buckets: dict[tuple[str, str], list[ActiveLearningItem]] = defaultdict(list)
    for it in items:
        buckets[(it.anomaly_type, it.flight_phase or "UNKNOWN")].append(it)
    for arr in buckets.values():
        arr.sort(key=lambda x: x.uncertainty_score, reverse=True)

    # Round-robin pick
    selected: list[ActiveLearningItem] = []
    bucket_keys = sorted(buckets.keys(),
                         key=lambda k: (buckets[k][0].uncertainty_score if buckets[k] else 0),
                         reverse=True)
    while len(selected) < top_k and bucket_keys:
        any_picked = False
        for k in list(bucket_keys):
            if buckets[k]:
                selected.append(buckets[k].pop(0))
                any_picked = True
                if len(selected) >= top_k:
                    break
            else:
                bucket_keys.remove(k)
        if not any_picked:
            break

    return selected[:top_k]


# ── P8-F · Human-in-the-loop approval ────────────────────────────────
VALID_DECISIONS = {"approved", "rejected", "modified", "deferred"}


@router.post(
    "/anomaly/approve",
    response_model=AnomalyApprovalResponse,
    dependencies=[Depends(require_analyst)],  # v2.2.0 · ADR-007 D4a RBAC
)
def approve_advisory(req: AnomalyApprovalRequest) -> AnomalyApprovalResponse:
    """Analyst decision on an LLM-generated advisory before broadcast.

    Writes immutable audit entry + Iceberg Gold + optional reject → suppress.

    Required flow for CRITICAL anomalies in production:
        1. IF detects anomaly → /detect/anomaly returns AnomalyEvent
        2. LLM generates advisory via /explain/anomaly
        3. Dashboard shows advisory side-by-side with raw data
        4. **Analyst clicks Approve/Reject** → this endpoint
        5. Only approved advisories are pushed to ATC broadcast channel
    """
    if req.decision not in VALID_DECISIONS:
        raise HTTPException(
            status_code=400,
            detail=f"decision must be one of {VALID_DECISIONS}",
        )
    if req.decision == "modified" and not req.modified_text:
        raise HTTPException(
            status_code=400,
            detail="decision=modified requires modified_text",
        )

    trace_id = ""
    try:
        from common.audit import audit_log, _trace_id  # type: ignore
        trace_id = _trace_id()
        audit_log(
            event="advisory_approval",
            actor=req.approver,
            resource=req.alert_id,
            outcome=req.decision,
            correlation_id=req.advisory_id,
            extra={
                "decision": req.decision,
                "reason": req.reason,
                "modified": bool(req.modified_text),
            },
        )
    except Exception:
        pass

    # Gold Iceberg write
    try:
        from feature_store.iceberg_writer import write_gold_anomaly_decision  # type: ignore
        write_gold_anomaly_decision(
            alert_id=req.alert_id,
            anomaly_type="advisory_gate",
            severity="approval",
            flight_phase=None,
            analyst_label=f"{req.decision}|{req.approver}",
        )
    except Exception:
        pass

    return AnomalyApprovalResponse(
        recorded=True,
        alert_id=req.alert_id,
        advisory_id=req.advisory_id,
        decision=req.decision,
        audit_trace_id=trace_id or None,
    )
