# SkyOps Intelligence Dashboard

항공 관제사·공항 운영자를 위한 실시간 의사결정 지원 UI.
FastAPI 백엔드(port 8000)의 지연 예측, 이상 탐지, RAG 어시스턴트 결과를
실시간 지도·히트맵·채팅 인터페이스로 노출한다.

---

## Stack

| 영역 | 기술 |
|------|------|
| 프레임워크 | **Next.js 16 (App Router)** + TypeScript |
| 스타일 | Tailwind CSS 4 |
| 지도 | `react-leaflet` (항공기 라이브맵), `maplibre-gl` + `h3-js` (H3 헥사곤 히트맵), `mapbox-gl` |
| 데이터 | SWR (REST + 폴링) + 브라우저 `WebSocket` (`/ws/aircraft`, `/ws/anomalies`) |
| 아이콘 | `lucide-react` |
| 린트/타입 | ESLint + TypeScript 5 |

> **Next.js 16 주의**: App Router 전용. `async` Server Components가 기본이며
> client 경계는 `"use client"`로 명시해야 한다. Pages Router 미지원. 자세한
> breaking changes는 `node_modules/next/dist/docs/` 참고.

---

## 페이지 (6종)

| Path | 파일 | 기능 |
|------|------|------|
| `/` | `src/app/page.tsx` | KPI 카드 4종 + 최근 알림 피드 + 항공기 요약 |
| `/map` | `src/app/map/page.tsx` | Leaflet 라이브맵 (WebSocket 3초 업데이트 + SWR fallback) |
| `/heatmap` | `src/app/heatmap/page.tsx` | MapLibre GL + H3 Resolution 5 혼잡도 히트맵 |
| `/anomaly` | `src/app/anomaly/page.tsx` | 이상 탐지 피드 + 심각도 필터 + AI 분석 버튼 |
| `/predict` | `src/app/predict/page.tsx` | XGBoost 지연 예측 + **90% Conformal interval** + 고급 Rotation 폼 |
| `/chat` | `src/app/chat/page.tsx` | RAG 어시스턴트 + 시나리오 3종 + 승객 안내문 |

---

## 개발 실행

```bash
cd dashboard
npm install
npm run dev
# → http://localhost:3000
```

**사전 조건**: FastAPI 서버가 `http://localhost:8000`에서 실행 중이어야 한다.

```bash
# 별도 터미널
cd ..
python serving/api.py
```

---

## 환경 변수

`dashboard/.env.local` (gitignored):

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# 선택: 지도 타일/토큰
NEXT_PUBLIC_MAPBOX_TOKEN=<your_mapbox_public_token>
```

API 클라이언트는 `src/lib/api.ts`에서 `NEXT_PUBLIC_API_URL`을 읽어 fetch 베이스로 사용한다. 운영 환경(Cloud Run 등)에서는 gateway의 public URL을 주입.

---

## Build & Deploy

```bash
npm run build
npm run start   # production server
```

- **Vercel 배포**: App Router 기본 설정으로 즉시 호환. 환경 변수는 Vercel 대시보드에서 설정.
- **Docker (옵션)**: `Dockerfile`을 추가해 multi-stage 빌드로 이미지 생성 (추후 [ADR-001 Migration Phase 3](../docs/adr/ADR-001-service-decomposition.md)).

---

## 디렉토리 구조

```
dashboard/
├── src/
│   ├── app/                  # App Router 페이지 (6종)
│   │   ├── layout.tsx        # 루트 레이아웃 + 사이드바
│   │   ├── page.tsx          # /
│   │   ├── map/page.tsx      # /map
│   │   ├── heatmap/page.tsx  # /heatmap
│   │   ├── anomaly/page.tsx  # /anomaly
│   │   ├── predict/page.tsx  # /predict (P1 Conformal interval + P1 Rotation form)
│   │   ├── chat/page.tsx     # /chat
│   │   └── globals.css
│   ├── components/
│   │   ├── layout/Sidebar.tsx       # 한국어 네비게이션
│   │   ├── map/AircraftMap.tsx      # Leaflet 항공기 마커
│   │   ├── map/HeatmapGL.tsx        # MapLibre GL 히트맵
│   │   └── shared/                  # Card, MetricCard, Badge 등
│   ├── hooks/
│   │   ├── useAircraftWS.ts         # WebSocket aircraft push
│   │   ├── useAnomalyFeed.ts        # SWR anomaly polling
│   │   └── useH3Heatmap.ts          # H3 grid aggregation
│   └── lib/
│       ├── types.ts                 # DelayRequest, DelayResponse, PredictionInterval, AnomalyEvent, ...
│       ├── api.ts                   # fetch wrapper
│       ├── constants.ts             # ICAO 공항 코드, 항공사 매핑
│       └── mock.ts                  # 개발용 fallback
├── public/                   # 정적 자산
├── package.json              # Next.js 16.2.2, React 19.2.4, Tailwind 4
├── next.config.ts
├── tsconfig.json
└── README.md                 # 이 파일
```

---

## 관련 문서

- [최상위 README](../README.md)
- [docs/event_model.md](../docs/event_model.md) — Canonical Event Model (7 이벤트 스키마)
- [docs/adr/ADR-001](../docs/adr/ADR-001-service-decomposition.md) — Backend service 분해 계획
- [docs/performance_benchmark.md](../docs/performance_benchmark.md) — 모델 성능 벤치마크 (P0~P3 업데이트 포함)
- Obsidian `06 - Dashboard` — 사내 노트

---

## API 계약

대시보드가 사용하는 FastAPI 엔드포인트 (전체 스펙은 백엔드 `/docs` Swagger):

- `GET /health`
- `POST /predict/delay` — **응답에 `prediction_interval` 포함** (P1 Conformal)
- `POST /predict/delay/batch`
- `POST /detect/anomaly` — **`flight_phase`, `suppressed` 필드 포함** (P2)
- `POST /anomaly/feedback` — 분석가 label 제출
- `POST /chat` — RAG 어시스턴트
- `POST /explain/anomaly`
- `POST /generate/announcement`
- `GET /aircraft/live`
- `GET /aircraft/h3`
- `GET /anomaly/recent`
- `WS /ws/aircraft` (3초 interval)
- `WS /ws/anomalies` (1초 interval)

백엔드 response shape 변경 시 `src/lib/types.ts` 먼저 동기화.

---

## 기여

- 사이드바 메뉴 추가: `src/components/layout/Sidebar.tsx`
- 새 페이지: `src/app/<route>/page.tsx`
- 타입 정의: `src/lib/types.ts` (백엔드와 동기 유지)
- 린트: `npm run lint`

PR 머지 전 체크리스트:
- [ ] `npm run build` 성공
- [ ] 타입 에러 없음
- [ ] 신규 환경변수는 README 환경 변수 섹션에 기록

---

## 참고 링크

- [Next.js 16 Docs](https://nextjs.org/docs) (App Router 중심)
- [react-leaflet](https://react-leaflet.js.org/)
- [MapLibre GL JS](https://maplibre.org/)
- [h3-js](https://h3geo.org/docs/api/indexing/)
- [SWR](https://swr.vercel.app/)
