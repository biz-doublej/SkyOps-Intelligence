# Architecture Decision Records (ADRs)

이 디렉토리는 SkyOps Intelligence의 **Architecture Decision Records**를 관리합니다.
MADR(Markdown Architecture Decision Records) 템플릿을 사용합니다.

---

## ADR 인덱스

| # | Title | Status | Date |
|---|-------|--------|------|
| [001](ADR-001-service-decomposition.md) | Service Decomposition — Split `serving/api.py` monolith into 6 microservices | **Accepted** (Phase 1, Phase 2) | 2026-04-14 |
| [002](ADR-002-api-gateway-selection.md) | API Gateway Selection — Traefik v3 for ADR-001 Phase 3 | **Proposed** | 2026-04-14 |

---

## ADR 작성 가이드

### Status lifecycle
- **Proposed** — 초안, 리뷰 중
- **Accepted** — 승인 완료, 구현 착수 가능
- **Rejected** — 채택 안 됨 (이유는 ADR 본문에 명시)
- **Deprecated** — 더 이상 유효하지 않음
- **Superseded by ADR-XXX** — 다른 ADR에 의해 대체됨

### Template (MADR 3.0)
```markdown
# ADR-{N}: {Title}

**Status**: Proposed | Accepted | Rejected | Deprecated | Superseded
**Date**: YYYY-MM-DD
**Deciders**: @names
**Technical Story**: [link to issue/ticket]

## Context and Problem Statement
...

## Decision Drivers
- ...

## Considered Options
1. ...
2. ...

## Decision Outcome
Chosen option: "..."

### Consequences
- Good: ...
- Bad: ...

## Pros and Cons of the Options
### Option 1
- Good: ...
- Bad: ...

## Migration Plan
...

## Verification / Metrics
...

## Links
- ...
```

### 새 ADR 추가 절차
1. `ADR-{NNN}-short-title.md` 파일 생성 (001, 002, ...)
2. 본 README의 인덱스 테이블에 추가
3. Status를 `Proposed`로 시작
4. PR 리뷰 후 `Accepted`/`Rejected` 결정

---

## 참고 자료
- [MADR 3.0 spec](https://adr.github.io/madr/)
- [Michael Nygard's "Documenting Architecture Decisions"](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) (원형)
- SkyOps Strategic Review: `2026-04-14 Strategic Review` 8번 병목 (Service Decomposition)
