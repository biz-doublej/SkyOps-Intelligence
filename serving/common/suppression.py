"""Alert suppression rules loader + matcher — v2.1.10 · ADR-006 D3.

운영 중 안정적인 이상 탐지를 위해 **이미 알려진 특수 상황** 에 대한 알람을
일시적으로 suppress 하는 규칙 엔진.

설계 원칙:
  1. Suppression 은 "알람 없애기" 가 아니라 "분석가 큐에서 제외" 로 정의.
     AnomalyResponse 는 여전히 suppressed=true 로 반환 + Redis Stream 에 감사 기록.
  2. 규칙은 YAML 단일 파일로 관리 — GitOps 검토 가능.
  3. 매칭은 정확(equality) 만 허용 — regex 금지 (실수로 전체 공항 suppress 방지).
  4. Cache: 파일 mtime 기반 hot-reload. 운영 중 YAML 편집 + 파일 저장 = 즉시 반영.

공공 API:
    SuppressionEngine.singleton()          # 전역 싱글턴
    engine.matches(flight_id, icao24, airport, at_time) -> (suppressed, reason)

Input 의 airport 은 origin / dest 둘 다 매칭 대상으로 들어온다 (caller 책임).
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SuppressionRule:
    kind: str             # "maintenance" | "weather" | "airport_closure"
    airport: str | None
    icao24: str | None
    starts_at: datetime
    ends_at: datetime
    reason: str
    owner: str | None = None

    def matches_at(self, now: datetime) -> bool:
        return self.starts_at <= now <= self.ends_at

    def matches_subject(self, *, airport: str | None, icao24: str | None) -> bool:
        if self.airport and airport and self.airport == airport:
            return True
        if self.icao24 and icao24 and self.icao24.lower() == icao24.lower():
            return True
        return False


def _parse_ts(s: str) -> datetime:
    # Accept "...Z" (RFC3339) and naive ISO.
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass
class SuppressionEngine:
    config_path: Path
    rules: list[SuppressionRule] = field(default_factory=list)
    _loaded_mtime: float = 0.0

    _singleton: "SuppressionEngine | None" = None

    @classmethod
    def singleton(cls) -> "SuppressionEngine":
        if cls._singleton is None:
            from .constants import SUPPRESSION_CONFIG
            cls._singleton = cls(config_path=SUPPRESSION_CONFIG)
            cls._singleton.reload_if_stale()
        else:
            cls._singleton.reload_if_stale()
        return cls._singleton

    def reload_if_stale(self) -> None:
        """mtime 기반 hot-reload — 파일이 없으면 rules=[] 로 유지 (fail-open 아님, fail-quiet)."""
        if not self.config_path.exists():
            if self.rules:
                logger.warning("suppression config 사라짐 → 규칙 비움: %s", self.config_path)
            self.rules = []
            self._loaded_mtime = 0.0
            return

        try:
            mtime = self.config_path.stat().st_mtime
        except OSError:
            return
        if mtime <= self._loaded_mtime and self.rules:
            return

        try:
            import yaml  # lazy import — only when engine is actually used
        except ImportError:
            logger.warning("PyYAML 미설치 → suppression 규칙 로드 불가. 모든 알람 통과.")
            self.rules = []
            self._loaded_mtime = mtime
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
        except Exception as e:  # noqa: BLE001
            logger.error("suppression config 파싱 실패 → 기존 규칙 유지: %s", e)
            return

        new_rules: list[SuppressionRule] = []
        for kind in ("maintenance", "weather", "airport_closure"):
            for entry in raw.get(kind) or []:
                try:
                    rule = SuppressionRule(
                        kind=kind,
                        airport=entry.get("airport"),
                        icao24=entry.get("icao24"),
                        starts_at=_parse_ts(entry["starts_at"]),
                        ends_at=_parse_ts(entry["ends_at"]),
                        reason=str(entry.get("reason", f"{kind}_suppression")),
                        owner=entry.get("owner"),
                    )
                    new_rules.append(rule)
                except Exception as e:  # noqa: BLE001
                    logger.warning("suppression rule skip (bad entry %r): %s", entry, e)
        self.rules = new_rules
        self._loaded_mtime = mtime
        logger.info("suppression rules reloaded: %d rules from %s",
                    len(self.rules), self.config_path)

    def matches(
        self, *,
        airport: str | None = None,
        icao24: str | None = None,
        at_time: datetime | None = None,
    ) -> tuple[bool, str | None, str | None]:
        """Return (suppressed, reason, rule_kind)."""
        now = (at_time or datetime.now(timezone.utc)).astimezone(timezone.utc)
        for rule in self.rules:
            if not rule.matches_at(now):
                continue
            if rule.matches_subject(airport=airport, icao24=icao24):
                return True, rule.reason, rule.kind
        return False, None, None


def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes", "on")


SUPPRESSION_ENABLED = _env_bool("SUPPRESSION_ENABLED", True)
