"""
SkyOps — Authentication & Role-Based Access Control (ADR-007 D4a · v2.2.0).

현 단계 (MVP → 운영 제품 전환기) 구현 범위:
  1. **Header 기반 신원** — Ingress/API Gateway 가 upstream OIDC 를 해석한 뒤
     다음 헤더를 API 에 전달한다고 가정:
        X-SkyOps-User   : user id (email or subject)
        X-SkyOps-Roles  : comma-separated roles (e.g., "analyst,admin")
  2. FastAPI `Depends(require_roles(...))` 로 엔드포인트별 authz.
  3. 헤더 없으면 기본 principal 은 `anonymous` / roles=[].
  4. env `SKYOPS_AUTH_ENFORCE=1` 일 때만 실제 차단. 0 이면 WARN 로그만
     남기고 통과 (dev 환경 grace 기간).

추후 (D4a Proposed → Accepted 업그레이드 시): FastAPI `HTTPBearer` + JWKS
verification 으로 직접 JWT 검증. 지금은 Ingress-offload 모델.

Audit log 연계: `common.audit` 이 request 의 principal 을 기록.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

from fastapi import Depends, Header, HTTPException, status

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes", "on")


AUTH_ENFORCE = _env_bool("SKYOPS_AUTH_ENFORCE", False)
AUTH_TRUSTED_HEADER_USER = os.getenv("SKYOPS_AUTH_USER_HEADER", "X-SkyOps-User")
AUTH_TRUSTED_HEADER_ROLES = os.getenv("SKYOPS_AUTH_ROLES_HEADER", "X-SkyOps-Roles")

# 역할 상수 — 매핑이 바뀌면 여기 한 곳만 수정.
ROLE_VIEWER = "viewer"    # 읽기 전용 (대시보드)
ROLE_ANALYST = "analyst"  # anomaly feedback, advisory approve/override
ROLE_ADMIN = "admin"      # 모델 재학습 트리거, suppression rule 변경


@dataclass(frozen=True)
class Principal:
    """인증된 주체. dev 환경에서 enforce=False 일 땐 anonymous 주체가 리턴됨."""
    user: str
    roles: list[str] = field(default_factory=list)
    authenticated: bool = False

    def has_role(self, role: str) -> bool:
        return role in self.roles or ROLE_ADMIN in self.roles  # admin 은 모든 역할 포함


def _extract_principal(user_header: str | None, roles_header: str | None) -> Principal:
    if not user_header:
        return Principal(user="anonymous", roles=[], authenticated=False)
    roles = [
        r.strip().lower() for r in (roles_header or "").split(",") if r.strip()
    ]
    return Principal(user=user_header.strip(), roles=roles, authenticated=True)


def get_principal(
    user_header: str | None = Header(default=None, alias=AUTH_TRUSTED_HEADER_USER),
    roles_header: str | None = Header(default=None, alias=AUTH_TRUSTED_HEADER_ROLES),
) -> Principal:
    """FastAPI dependency — 현재 요청의 주체를 리턴. 인증 실패 시에도 Principal(anonymous) 리턴.

    `require_roles()` 가 그 위에서 실제 역할 검사를 수행한다.
    """
    return _extract_principal(user_header, roles_header)


def require_roles(*required_roles: str):
    """Dependency factory — 지정된 role 중 하나라도 있으면 통과.

    사용:
        @router.post("/anomaly/approve",
                     dependencies=[Depends(require_roles(ROLE_ANALYST, ROLE_ADMIN))])

    AUTH_ENFORCE=0 일 때는 WARN 로그만 남기고 통과 (dev grace).
    """
    required = tuple(r.lower() for r in required_roles)

    def dep(principal: Principal = Depends(get_principal)) -> Principal:
        allowed = any(principal.has_role(r) for r in required)
        if allowed:
            return principal
        if not AUTH_ENFORCE:
            logger.warning(
                "authz soft-deny (enforce off): principal=%s roles=%s required=%s",
                principal.user, principal.roles, required,
            )
            return principal
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"권한 부족: {required} 중 하나가 필요합니다. "
                f"현재 roles={principal.roles or '[]'}."
            ),
        )
    return dep


# 편의 shortcut — 흔한 조합.
require_analyst = require_roles(ROLE_ANALYST, ROLE_ADMIN)
require_admin = require_roles(ROLE_ADMIN)
