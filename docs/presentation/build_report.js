// SkyOps Intelligence — 최종 보고서 (한글 DOCX → PDF)
// 실행: node build_report.js

const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat, ExternalHyperlink,
  TableOfContents, HeadingLevel, BorderStyle, WidthType, ShadingType,
  VerticalAlign, PageNumber, PageBreak,
} = require("docx");

// ─────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────
const FONT = "Malgun Gothic";  // 한글 기본
const FONT_MONO = "Consolas";

function p(text, opts = {}) {
  return new Paragraph({
    alignment: opts.align || AlignmentType.JUSTIFIED,
    spacing: { line: 360, after: opts.after ?? 120, before: opts.before ?? 0 },
    children: [new TextRun({
      text, font: opts.mono ? FONT_MONO : FONT, size: opts.size || 22,
      bold: opts.bold || false, italics: opts.italic || false, color: opts.color || "000000",
    })],
  });
}

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 240 },
    children: [new TextRun({ text, font: FONT, size: 32, bold: true, color: "1E3A5F" })],
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 240, after: 160 },
    children: [new TextRun({ text, font: FONT, size: 26, bold: true, color: "1E88E5" })],
  });
}

function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 200, after: 120 },
    children: [new TextRun({ text, font: FONT, size: 22, bold: true, color: "263238" })],
  });
}

function richP(parts, opts = {}) {
  return new Paragraph({
    alignment: opts.align || AlignmentType.JUSTIFIED,
    spacing: { line: 360, after: opts.after ?? 120 },
    children: parts.map(part => {
      if (typeof part === "string") {
        return new TextRun({ text: part, font: FONT, size: 22 });
      }
      return new TextRun({
        text: part.text, font: part.mono ? FONT_MONO : FONT, size: part.size || 22,
        bold: part.bold || false, italics: part.italic || false, color: part.color || "000000",
      });
    }),
  });
}

function bullet(text, level = 0) {
  return new Paragraph({
    numbering: { reference: "bullets", level },
    spacing: { line: 320, after: 80 },
    children: [new TextRun({ text, font: FONT, size: 22 })],
  });
}

function richBullet(parts, level = 0) {
  return new Paragraph({
    numbering: { reference: "bullets", level },
    spacing: { line: 320, after: 80 },
    children: parts.map(part => {
      if (typeof part === "string") return new TextRun({ text: part, font: FONT, size: 22 });
      return new TextRun({
        text: part.text, font: part.mono ? FONT_MONO : FONT, size: part.size || 22,
        bold: part.bold || false, italics: part.italic || false, color: part.color || "000000",
      });
    }),
  });
}

function numberedP(text, level = 0) {
  return new Paragraph({
    numbering: { reference: "numbers", level },
    spacing: { line: 320, after: 80 },
    children: [new TextRun({ text, font: FONT, size: 22 })],
  });
}

function code(text) {
  return new Paragraph({
    spacing: { line: 280, after: 120 },
    shading: { type: ShadingType.CLEAR, fill: "F5F5F5" },
    children: [new TextRun({ text, font: FONT_MONO, size: 18, color: "263238" })],
  });
}

function quote(text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { line: 360, after: 160, before: 120 },
    border: { left: { style: BorderStyle.SINGLE, size: 24, color: "1E88E5", space: 12 } },
    indent: { left: 400 },
    children: [new TextRun({ text: `"${text}"`, font: FONT, size: 24, italics: true, color: "37474F" })],
  });
}

function tableRow(cells, isHeader = false, widths = null) {
  return new TableRow({
    tableHeader: isHeader,
    children: cells.map((cell, i) => new TableCell({
      width: { size: widths ? widths[i] : undefined, type: WidthType.DXA },
      shading: isHeader ? { type: ShadingType.CLEAR, fill: "1E3A5F" } : { type: ShadingType.CLEAR, fill: "FFFFFF" },
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      borders: {
        top: { style: BorderStyle.SINGLE, size: 4, color: "BDBDBD" },
        bottom: { style: BorderStyle.SINGLE, size: 4, color: "BDBDBD" },
        left: { style: BorderStyle.SINGLE, size: 4, color: "BDBDBD" },
        right: { style: BorderStyle.SINGLE, size: 4, color: "BDBDBD" },
      },
      children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { line: 280 },
        children: [new TextRun({
          text: String(cell), font: FONT, size: 20,
          bold: isHeader, color: isHeader ? "FFFFFF" : "000000",
        })],
      })],
    })),
  });
}

function simpleTable(rows, widths) {
  const totalWidth = widths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: totalWidth, type: WidthType.DXA },
    columnWidths: widths,
    rows: rows.map((row, i) => tableRow(row, i === 0, widths)),
  });
}

// ─────────────────────────────────────────────────────
// 문서 내용
// ─────────────────────────────────────────────────────
const children = [];

// ══════════ 표지 ══════════
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 2400, after: 480 },
  children: [new TextRun({ text: "2026학년도 1학기 캡스톤디자인", font: FONT, size: 24, color: "78909C" })],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 240 },
  children: [new TextRun({ text: "최종 보고서", font: FONT, size: 32, bold: true, color: "78909C" })],
}));

children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 800, after: 240 },
  children: [new TextRun({ text: "SkyOps Intelligence", font: FONT, size: 64, bold: true, color: "1E3A5F" })],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 480 },
  children: [new TextRun({ text: "실시간 항공 운항 이상 탐지 및 AI 관제 보조 플랫폼", font: FONT, size: 28, color: "263238" })],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 240, after: 1200 },
  children: [new TextRun({
    text: "「이상을 탐지하고, 원인을 설명하고, 대응 절차를 5초 이내에 자동 생성합니다」",
    font: FONT, size: 22, italics: true, color: "1E88E5",
  })],
}));

children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 1600, after: 120 },
  children: [new TextRun({ text: "발  표  자", font: FONT, size: 22, color: "78909C" })],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 480 },
  children: [new TextRun({ text: "정 재 원  (DoubleJ팀)", font: FONT, size: 28, bold: true, color: "263238" })],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 120 },
  children: [new TextRun({ text: "지  도  교  수", font: FONT, size: 22, color: "78909C" })],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 480 },
  children: [new TextRun({ text: "조 상 구  교  수  님", font: FONT, size: 28, bold: true, color: "263238" })],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 120 },
  children: [new TextRun({ text: "소  속", font: FONT, size: 22, color: "78909C" })],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 1200 },
  children: [new TextRun({ text: "빅 데 이 터 과", font: FONT, size: 28, bold: true, color: "263238" })],
}));

children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 800 },
  children: [new TextRun({ text: "2026 년 04 월 16 일", font: FONT, size: 24, color: "263238" })],
}));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ══════════ 요약 ══════════
children.push(h1("0. 요약 (Executive Summary)"));

children.push(richP([
  { text: "SkyOps Intelligence", bold: true, color: "1E3A5F" },
  "는 실시간 항공 운항 데이터를 수집하여 지연 예측·이상 탐지·AI 관제 보조를 제공하는 엔드투엔드 AI 플랫폼이다. 본 프로젝트는 2026년 1학기 캡스톤디자인의 15주 커리큘럼 위에 2026-04-14부터 04-16까지 총 ",
  { text: "8회의 엔터프라이즈급 Sprint (P0~P8)", bold: true },
  "를 추가 진행하여 대학 MVP를 production-ready 플랫폼으로 격상시켰다.",
]));

children.push(p("핵심 성과는 다음과 같다:"));
children.push(bullet("지연 예측 모델 (XGBoost + Conformal Prediction) Test R² 0.4328, 분류 정확도 89.04%, 90% 신뢰구간 coverage 달성"));
children.push(bullet("이상 탐지 모델 (Per-phase Isolation Forest ×7) — 비행 단계별 별도 모델로 alert fatigue 67% 감소"));
children.push(bullet("한국어 특화 LLM (Qwen2.5-7B + QLoRA + DPO) — Eval Token Accuracy 97.88%, DPO Rewards Accuracy 100%"));
children.push(bullet("RAG 시스템 (ChromaDB 161 chunks + BAAI/bge-m3) — FAA AIM, ICAO Annex, RKSI 특화 코퍼스 통합"));
children.push(bullet("FAA SWIM 실시간 연동 — 60초에 실제 NOTAM 219건 수신 검증 (received=219, published=219, parse_err=0)"));
children.push(bullet("Next.js 16 기반 관제 대시보드 7 페이지 — 실시간 지도·히트맵·AI 어시스턴트 통합"));
children.push(bullet("엔터프라이즈 인프라 — MLflow, Airflow, Feast Feature Store, Apache Iceberg, OpenLineage, Prometheus, Grafana, Jaeger, Argo Rollouts, Cosign + SBOM"));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ══════════ 목차 ══════════
children.push(h1("목차"));
const toc = [
  ["0. 요약", "1"],
  ["1. 프로젝트 개요", "3"],
  ["   1.1 배경과 목적", "3"],
  ["   1.2 문제 정의", "3"],
  ["   1.3 해결 접근", "4"],
  ["2. 시스템 아키텍처", "5"],
  ["   2.1 5-Layer 구조", "5"],
  ["   2.2 데이터 흐름", "6"],
  ["3. 데이터 파이프라인", "7"],
  ["   3.1 데이터 소스 4종", "7"],
  ["   3.2 Kafka + Avro Schema Registry", "8"],
  ["   3.3 PyFlink + Redis", "9"],
  ["4. ML 모델 — 지연 예측", "10"],
  ["   4.1 XGBoost 선택 배경", "10"],
  ["   4.2 TimeSeriesSplit 전환 (P0)", "11"],
  ["   4.3 Rotation Features (P1)", "12"],
  ["   4.4 Conformal Prediction", "13"],
  ["5. ML 모델 — 이상 탐지", "14"],
  ["   5.1 Isolation Forest 원리", "14"],
  ["   5.2 Per-phase IF ×7 (P5+)", "15"],
  ["   5.3 Active Learning Loop", "16"],
  ["6. LLM — AI 어시스턴트", "17"],
  ["   6.1 Qwen2.5-7B 선택 이유", "17"],
  ["   6.2 QLoRA 4-bit Fine-tuning", "18"],
  ["   6.3 DPO 선호도 학습", "19"],
  ["   6.4 RAG + ChromaDB", "20"],
  ["7. 서빙 및 대시보드", "21"],
  ["   7.1 FastAPI + vLLM", "21"],
  ["   7.2 Next.js 16 Dashboard", "22"],
  ["8. MLOps & Engineering Package", "23"],
  ["   8.1 실험 관리 및 데이터 거버넌스", "23"],
  ["   8.2 관측성 스택", "24"],
  ["   8.3 k8s + Helm + Terraform", "25"],
  ["   8.4 CI/CD + Supply-chain Security", "26"],
  ["9. 성능 평가", "27"],
  ["10. 한계 및 향후 계획", "29"],
  ["11. 결론", "30"],
  ["12. 참고문헌", "31"],
];
toc.forEach(([title, page]) => {
  children.push(new Paragraph({
    spacing: { line: 320, after: 40 },
    tabStops: [{ type: "right", position: 9000 }],
    children: [
      new TextRun({ text: title, font: FONT, size: 22 }),
      new TextRun({ text: "\t" + page, font: FONT, size: 22, color: "78909C" }),
    ],
  }));
});

children.push(new Paragraph({ children: [new PageBreak()] }));

// ══════════ 1. 프로젝트 개요 ══════════
children.push(h1("1. 프로젝트 개요"));

children.push(h2("1.1 배경과 목적"));
children.push(p("항공 운항은 매 순간 안전과 효율의 균형을 요구한다. 관제사는 30초 이내에 결정을 내려야 하고, 그 결정 하나가 수백 명의 안전과 수억 원의 비용에 영향을 미친다. 그럼에도 현재 관제 지원 시스템은 수십 년 된 Rule 기반이 대부분이며, 최근 5년간 발표된 항공 AI 논문의 대부분은 실제 운영 시스템에 통합되지 못했다."));
children.push(p("SkyOps Intelligence는 이 간극을 메우는 것을 목표로 한다. 학습된 모델이 단순히 예측만 내놓는 것이 아니라, 예측의 불확실성을 정량적으로 제시하고, 원인을 자연어로 설명하며, 관련 대응 절차까지 제안하는 \"Advisory Copilot\"을 구현했다."));

children.push(h2("1.2 문제 정의"));
children.push(p("현재 항공 운영 의사결정 지원의 3대 구조적 한계를 다음과 같이 정의했다."));

children.push(h3("(1) 불투명한 지연 예측"));
children.push(p("기존 지연 예측 모델은 단일 숫자 (예: \"15분 지연\") 만 제공한다. 관제사는 이 숫자를 얼마나 신뢰할 수 있는지 모른 채 승객 안내·게이트 재배정·대체편 투입 여부를 결정해야 한다. 실제 지연은 동일한 예측값에 대해 5분일 수도, 40분일 수도 있기 때문에 정량적 위험 관리가 불가능하다."));

children.push(h3("(2) 과다한 False Positive (Alert Fatigue)"));
children.push(p("단일 임계값 기반 이상 탐지 Rule 은 이륙 중 정상적 급상승까지 이상으로 분류한다. 관제사는 반복되는 false alarm 에 무감각해지고, 실제 긴급 상황의 초기 대응이 늦어질 위험이 발생한다. EUROCONTROL은 2023년 보고서에서 alert fatigue가 유럽 항공 사고의 12%에 간접적으로 기여했다고 분석했다."));

children.push(h3("(3) 비상 상황 의사결정 보조의 부재"));
children.push(p("FAA Aeronautical Information Manual(AIM)은 약 800페이지, ICAO Annex 시리즈는 19권 총 3,200페이지이다. 비상 상황에서 관련 절차를 즉시 참조하는 것은 사실상 불가능하며, 경험 많은 관제사의 암묵지에 의존하고 있다."));

children.push(h2("1.3 해결 접근"));
children.push(p("SkyOps Intelligence는 위 3대 한계에 대해 각각 다음 기술로 대응한다."));

children.push(richP([
  { text: "확률적 예측:  ", bold: true, color: "1E88E5" },
  "MAPIE 라이브러리의 Split Conformal Prediction 및 Conformalized Quantile Regression을 적용하여 ",
  { text: "\"90% 확률로 6~41분 지연\"", bold: true },
  " 형태의 수학적으로 유효한 예측구간을 제공한다. 분포 가정 없이 coverage 90%가 이론적으로 보장된다.",
]));

children.push(richP([
  { text: "Phase-aware 탐지:  ", bold: true, color: "1E88E5" },
  "비행 단계(TAXI / TAKEOFF / CLIMB / CRUISE / DESCENT / APPROACH / LANDING) 별로 독립된 Isolation Forest 모델 7개를 학습하고, 단계마다 ",
  { text: "contamination 파라미터를 도메인 지식 기반으로 튜닝", bold: true },
  " (TAXI 0.02, APPROACH/LANDING 0.06)하여 false positive 67% 감소를 달성했다.",
]));

children.push(richP([
  { text: "AI 어시스턴트:  ", bold: true, color: "1E88E5" },
  "Qwen2.5-7B 모델을 QLoRA로 항공 도메인 데이터 13,969건에 fine-tuning하고, DPO로 한국어 선호도를 정렬한 후, RAG 기법으로 FAA AIM·ICAO Annex·RKSI SOP 등 ",
  { text: "161개 문서 chunk를 실시간 참조", bold: true },
  "하여 5초 이내 답변을 생성한다.",
]));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ══════════ 2. 시스템 아키텍처 ══════════
children.push(h1("2. 시스템 아키텍처"));

children.push(h2("2.1 5-Layer 구조"));
children.push(p("SkyOps Intelligence는 책임 분리(separation of concerns) 원칙에 따라 5개 Layer로 구성된다. 각 Layer는 독립적 테스트·배포·교체가 가능하며, Layer 간 통신은 명시적 계약(Kafka topic + Avro schema)을 통해서만 이루어진다."));

children.push(simpleTable([
  ["Layer", "역할", "주요 기술"],
  ["Layer 1", "데이터 수집", "OpenSky ADS-B · NOAA METAR · FAA SWIM · KAC ACDM"],
  ["Layer 2", "스트리밍 처리", "Apache Kafka + Avro Schema Registry · PyFlink · Redis"],
  ["Layer 3", "AI 모델", "XGBoost · Per-phase IF ×7 · Qwen2.5-7B · ChromaDB RAG"],
  ["Layer 4", "서빙", "FastAPI 15 endpoints · vLLM AWQ · WebSocket 3종"],
  ["Layer 5", "대시보드", "Next.js 16 · 7 페이지 · Cloudflare Tunnel"],
], [1440, 2160, 5760]));

children.push(h2("2.2 데이터 흐름"));
children.push(p("원천 데이터가 Layer 1에서 수집되어 Kafka topic에 publish되고, PyFlink가 5분 윈도우 집계를 수행한 뒤 Redis에 hot state로 캐싱된다. AI 모델은 Redis에서 feature를 읽거나 Feast Feature Store의 online layer를 조회하며, 추론 결과는 FastAPI를 통해 대시보드에 REST/WebSocket으로 제공된다."));
children.push(p("핵심 설계 원칙은 다음과 같다."));
children.push(bullet("Unidirectional data flow — 상위 Layer는 하위 Layer를 직접 호출하지 않고 이벤트 구독으로만 연결"));
children.push(bullet("Canonical event model — 7 종 canonical event (FlightLeg, TailRotation, SurfaceMovement, Weather, ATFMRestriction, NOTAM, AlertDecision) 정의"));
children.push(bullet("Schema evolution — Avro BACKWARD compatibility 로 필드 추가는 안전, 삭제는 금지"));
children.push(bullet("Immutable audit log — 모든 결정 이벤트는 JSONL append-only 로그에 OTel trace_id와 함께 기록"));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ══════════ 3. 데이터 파이프라인 ══════════
children.push(h1("3. 데이터 파이프라인"));

children.push(h2("3.1 데이터 소스 4종"));

children.push(h3("(1) OpenSky Network"));
children.push(p("유럽 항공관제 연구소가 2013년 시작한 공개 ADS-B 데이터 플랫폼. 전 세계 약 35,000개 지상 수신기가 익명으로 기여하며, 항공기 위치·고도·속도를 10초 주기로 제공한다. 저희 시스템은 한반도 영공 (북위 33~39도, 동경 124~132도) 범위의 항공기를 pipeline/opensky_producer.py 를 통해 Kafka topic 'flight-position' 에 publish한다."));

children.push(h3("(2) NOAA/KMA METAR"));
children.push(p("METAR(METeorological Aerodrome Report)는 ICAO 표준 공항 기상 관측 포맷이다. NOAA는 전 세계 데이터를, 기상청(KMA)는 국내 공항 데이터를 30분 주기로 발표한다. 바람·시정·운고·기온이 지연의 가장 큰 단일 원인이므로 XGBoost feature로 직접 투입한다."));

children.push(h3("(3) FAA SWIM (System Wide Information Management)"));
children.push(p("미 연방항공청이 2006년 시작한 차세대 항공 정보 공유 인프라. Solace PubSub+ JMS 브로커 (ems2.swim.faa.gov:55443) 에 구독 계약을 맺고 TLS 1.2 암호화 연결을 통해 실시간 NOTAM을 수신한다. 본 프로젝트에서는 AIXM 5.1 XML을 FAA 전용 event: namespace 를 포함해 파싱하고, Q-code (QNDAS, QMRLC 등) 를 canonical NOTAM class로 매핑한다."));

children.push(richP([
  { text: "실측 검증: ", bold: true, color: "1E88E5" },
  "SWIM_RUN_SECONDS=60으로 60초 구독 실행 결과 ",
  { text: "received=219, published=219, parse_err=0", bold: true, mono: true, color: "00897B" },
  ". 실제 FAA 시스템에서 실시간 NOTAM 수신에 성공했다.",
]));

children.push(h3("(4) 한국공항공사 ACDM 공공데이터"));
children.push(p("공공데이터포털 (data.go.kr) 의 인천국제공항공사 운항정보 API. EUROCONTROL NM B2B 계약이 없는 상황에서 한국 공항 trafffic의 지연 상황을 추정하는 대안 경로로 활용한다. pipeline/kac_acdm_client.py 에서 fetch_recent_delays로 최근 지연 항공편을 조회하고, derive_restrictions_from_delays heuristic으로 ATFM GDP/CTOT 를 추정한다."));

children.push(new Paragraph({ children: [new PageBreak()] }));

children.push(h2("3.2 Apache Kafka + Avro Schema Registry"));
children.push(p("Kafka를 채택한 이유는 4가지로 정리된다."));
children.push(numberedP("처리량 — ADS-B는 초당 수천 건 이벤트. HTTP REST는 backpressure 감당 불가. Kafka의 pub-sub + 로그 저장 모델은 선형 확장 가능"));
children.push(numberedP("Multi-consumer — 동일 데이터를 이상 탐지, 지연 예측, 대시보드가 동시 소비. Kafka의 consumer group이 파티션 단위로 병렬 처리"));
children.push(numberedP("재처리 가능성 — 새 모델 배포 시 \"어제 14:00부터 재처리\"가 log offset 조작만으로 가능"));
children.push(numberedP("Schema enforcement — Confluent Avro Schema Registry와 결합하면 producer가 잘못된 필드를 보낼 때 즉시 reject"));

children.push(p("본 프로젝트는 6개 canonical topic을 정의했다."));
children.push(simpleTable([
  ["Topic", "Event Type", "Schema Version"],
  ["flight-position", "FlightPositionEvent", "2.0"],
  ["weather-event", "WeatherEvent", "2.0"],
  ["notam", "NOTAMEvent", "2.0"],
  ["atfm-restriction", "ATFMRestrictionEvent", "2.0"],
  ["alert-decision", "AlertDecisionEvent", "2.0"],
  ["acdm-milestone", "ACDMMilestoneEvent (P8)", "2.0"],
], [3120, 3600, 2640]));

children.push(h2("3.3 PyFlink + Redis"));

children.push(h3("PyFlink — True Streaming"));
children.push(p("Apache Spark Streaming은 micro-batch 방식 (2-5초 지연)이지만, Apache Flink는 이벤트 단위 진짜 스트리밍이다. 항공처럼 실시간성이 critical 한 도메인에서는 Flink가 적합하다. 특히 event-time + watermark 메커니즘으로 네트워크 지연으로 늦게 도착하는 ADS-B 이벤트도 올바른 시간 기준으로 집계 가능하다."));

children.push(p("pipeline/flink_processor.py는 5분 Tumbling Window를 적용하여 공항별 시간당 출발/도착 편수 (origin_hourly_departures, dest_hourly_arrivals)를 실시간 계산하고, XGBoost feature로 제공한다. 또한 CEP(Complex Event Processing) 룰 엔진으로 비정상 패턴을 탐지한다."));

children.push(h3("Redis — Low-latency State Store"));
children.push(p("관제사 대시보드는 실시간 항공기 위치를 표시하기 위해 p95 < 30ms 응답이 필요하다. PostgreSQL 같은 디스크 DB는 5-50ms 범위이지만 Redis는 마이크로초 단위다. aircraft state는 Redis Sorted Set에 캐싱하고, 이상 탐지의 debouncing(알람 억제)도 TTL 60초 key로 구현한다."));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ══════════ 4. ML 모델 — 지연 예측 ══════════
children.push(h1("4. ML 모델 — 지연 예측"));

children.push(h2("4.1 XGBoost 선택 배경"));
children.push(p("지연 예측 모델로 XGBoost(Extreme Gradient Boosting)를 선택했다. XGBoost는 2014년 Tianqi Chen이 발표한 Gradient Boosting 알고리즘으로, tabular 데이터에서 사실상 업계 표준이다. Kaggle 대회의 우승 모델 대부분이 XGBoost 또는 파생 모델(LightGBM, CatBoost)을 사용한다."));

children.push(h3("선택 이유"));
children.push(richBullet([
  { text: "정확도: ", bold: true },
  "tabular 데이터(수치형·범주형 혼합)에서 딥러닝 대비 동등 이상 성능. 피처가 20-30개 수준일 때 특히 강세",
]));
children.push(richBullet([
  { text: "속도: ", bold: true },
  "히스토그램 기반 split + 병렬 학습으로 5.7M rows를 RTX 3070 없이 CPU 만으로 4분에 학습 완료",
]));
children.push(richBullet([
  { text: "해석성: ", bold: true },
  "SHAP TreeExplainer 완벽 지원. \"왜 이 항공편이 15분 지연된다고 예측했는가\"를 feature 기여도로 시각화. 관제사에게 근거 제시 가능",
]));
children.push(richBullet([
  { text: "Robustness: ", bold: true },
  "결측값 자동 처리, 이상치에 강함, normalization 불필요",
]));

children.push(h3("대안 검토 결과"));
children.push(simpleTable([
  ["대안", "장점", "단점 (선택하지 않은 이유)"],
  ["LightGBM", "XGBoost 대비 ~10% 빠름", "overfitting 성향, tabular 안정성 낮음"],
  ["CatBoost", "범주형 feature 자동 처리", "수치형 우세인 본 프로젝트에 이점 적음"],
  ["Random Forest", "병렬 학습 단순", "gradient boosting 대비 성능 낮음"],
  ["Neural Network", "복잡한 관계 모델링 가능", "tabular 20~30 feature에서 XGBoost 대비 열세"],
], [1440, 3120, 4800]));

children.push(h2("4.2 TimeSeriesSplit 전환 (P0)"));
children.push(p("프로젝트 초기 코드는 sklearn KFold(shuffle=True)를 사용하고 있었다. 이는 시계열 데이터에서 치명적 오류인 temporal leakage를 일으킨다 — 미래 데이터로 과거를 예측하게 되어 실제 성능보다 과대평가된 지표를 만든다."));
children.push(p("P0 Sprint에서 TimeSeriesSplit으로 전환하여 walk-forward validation을 적용했다. 각 fold는 과거 데이터로 학습하고 미래 데이터로 평가한다."));

children.push(richP([
  { text: "결과 (Before vs After):", bold: true },
]));
children.push(simpleTable([
  ["지표", "KFold shuffle", "TimeSeriesSplit", "해석"],
  ["Best Optuna RMSE", "24.64 (val)", "31.80 (TSCV)", "정직한 숫자로 전환"],
  ["5-Fold CV std", "±0.30", "±6.14", "변동성 20배 노출"],
  ["Test RMSE", "36.59", "36.52", "동등"],
  ["Test R²", "0.096", "0.0996", "미약 개선"],
], [2160, 2160, 2160, 2880]));

children.push(p("CV 표준편차가 20배 증가한 것은 \"나쁜 결과\"가 아니다. shuffle이 숨기고 있던 시간대별 성능 변동성이 정직하게 드러난 것이며, 이 변동성의 원인을 찾는 것이 P1의 출발점이 되었다."));

children.push(new Paragraph({ children: [new PageBreak()] }));

children.push(h2("4.3 Rotation Features (P1)"));
children.push(p("EUROCONTROL CODA(Central Office for Delay Analysis) 2019 보고서에 따르면, 유럽 항공 지연의 45%가 reactionary delay 즉 전편 지연의 누적 파급 효과이다. 기존 저희 모델은 항공편을 독립 변수로만 취급하여 이 효과를 놓치고 있었다."));

children.push(p("P1 Sprint에서 동일 항공기(tail number)의 운항 네트워크를 반영하는 5개 feature를 추가했다."));

children.push(simpleTable([
  ["Feature", "설명"],
  ["rotation_depth", "오늘 해당 항공기의 몇 번째 비행인지 (0=첫편, 1=두번째, ...)"],
  ["prev_leg_arr_delay_min", "직전 비행의 도착 지연 (분) — reactionary의 핵심 변수"],
  ["scheduled_turnaround_min", "예정 게이트 체류 시간"],
  ["actual_turnaround_min", "실제 게이트 체류 시간"],
  ["is_first_leg_of_day", "첫 비행 여부 (1 or 0)"],
], [3600, 5760]));

children.push(p("동일 XGBoost 모델에 feature 5개만 추가한 결과는 극적이었다."));

children.push(simpleTable([
  ["지표", "P0 (20 features)", "P1 (25 features)", "변화"],
  ["Val RMSE", "24.60", "22.61", "-8.1%"],
  ["Test RMSE", "36.52", "28.18", "-22.8%"],
  ["Test R²", "0.0996", "0.4328", "+335% !"],
  ["Delay Acc (Test)", "84.16%", "89.04%", "+4.88%p"],
  ["CV std", "±6.14", "±1.51", "4배 안정"],
  ["Val-Test gap", "12분", "5.5분", "절반"],
], [2400, 1920, 1920, 1920]));

children.push(p("이 결과는 \"모델을 키우는 것보다 도메인 지식이 중요하다\"는 원칙을 실증한 사례이다. Test R² 0.43은 관제사에게 실질적 의사결정 지원이 가능한 수준이다."));

children.push(h2("4.4 Conformal Prediction"));
children.push(p("Test R² 0.43은 \"평균적 정확도\"일 뿐 개별 예측의 신뢰도를 알려주지 않는다. 관제사가 \"이 예측이 얼마나 확실한가\"를 알아야 정량적 위험 판단이 가능하다."));

children.push(p("Conformal Prediction은 분포 가정 없이 유효 예측구간을 보장하는 기법이다. 2005년 Vovk와 Shafer가 제안했으며, 최근 ICML, NeurIPS 최고 학술대회에서 활발히 연구되고 있다."));

children.push(h3("Split Conformal — P1"));
children.push(numberedP("학습 데이터를 train + calibration + test 3부분으로 분할"));
children.push(numberedP("XGBoost를 train set으로 학습"));
children.push(numberedP("Calibration set의 각 샘플에 대해 |예측값 - 실제값| 즉 절대 residual 계산"));
children.push(numberedP("90% 분위수(Q90)를 conformity score로 취함"));
children.push(numberedP("새 샘플 예측 시 [ŷ - Q90, ŷ + Q90] 을 90% 예측구간으로 제공"));

children.push(richP([
  { text: "실측 결과: ", bold: true, color: "1E88E5" },
  "Empirical coverage ",
  { text: "90.00%", bold: true, color: "00897B" },
  " (목표 90% 정확 달성), 평균 interval width ",
  { text: "30.84분", bold: true, color: "00897B" },
  ". 예시: \"예상 지연 18분, 90% 확률로 6~41분\"",
]));

children.push(h3("Conformalized Quantile Regression (CQR) — P4+"));
children.push(p("Split Conformal은 좌우 대칭 interval을 생성한다. 그러나 기상·혼잡도의 영향으로 지연 분포는 한쪽으로 치우친 경우가 많다. CQR은 low/high quantile regressor 2개를 별도 학습하여 비대칭 interval을 생성한다."));
children.push(p("sklearn GradientBoostingRegressor의 quantile loss로 α/2 (하단) 및 1-α/2 (상단) quantile을 학습한 뒤, MAPIE ConformalizedQuantileRegressor로 conformity score를 적용했다. Coverage는 동일 90%, average width는 33.23분(split 대비 근소 증가)이나 비대칭 분포를 더 정확히 반영한다."));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ══════════ 5. ML 모델 — 이상 탐지 ══════════
children.push(h1("5. ML 모델 — 이상 탐지"));

children.push(h2("5.1 Isolation Forest 원리"));
children.push(p("이상 탐지(anomaly detection)는 정상 vs 이상 데이터의 class imbalance가 극단적(정상 99.9% vs 이상 0.1%)이고, 실제 사고 데이터는 희귀하여 label이 부족하다. 따라서 비지도 학습이 필수적이다."));

children.push(p("Isolation Forest(Liu et al., 2008)는 \"이상치는 소수이고 다른 데이터와 거리가 멀다\"는 직관에서 출발한다. 랜덤 트리로 데이터를 재귀적으로 분할하면, 정상 데이터는 깊은 트리까지 가서야 isolation되지만 이상 데이터는 얕은 트리에서 빨리 분리된다. 여러 트리의 평균 path length를 anomaly score로 계산한다."));

children.push(h3("대안 검토"));
children.push(simpleTable([
  ["대안", "단점"],
  ["Autoencoder", "GPU 필요, 학습 안정성 낮음, hyperparameter 민감"],
  ["One-class SVM", "O(n²~n³) 복잡도, 대용량에 느림"],
  ["통계 임계값", "단일 rule로는 단계별 정상 분포 차이 반영 불가"],
  ["LSTM Autoencoder", "시계열 학습 복잡, 현재 feature로도 충분"],
], [3600, 5760]));

children.push(h2("5.2 Per-phase IF ×7 (P5+)"));
children.push(p("이상 탐지의 핵심 개선은 \"비행 단계별로 정상의 범위가 완전히 다르다\"는 도메인 통찰에서 시작되었다. CRUISE 중 30,000ft는 정상이지만 LANDING 중 30,000ft는 비정상이다. 단일 모델은 이 두 상황을 구분할 수 없다."));

children.push(p("P5+ Sprint에서 7개 단계별로 별도 Isolation Forest 모델을 학습했다. 각 단계의 contamination 파라미터는 도메인 지식 기반으로 튜닝했다."));

children.push(simpleTable([
  ["Phase", "Contamination", "근거"],
  ["TAXI", "0.02", "지상 이동 — 이상 발생률 낮음"],
  ["TAKEOFF", "0.03", "이륙 — 표준 profile 뚜렷"],
  ["CLIMB", "0.04", "상승 — 일정 VS"],
  ["CRUISE", "0.05", "순항 — 대부분 시간 차지, baseline"],
  ["DESCENT", "0.04", "하강 — -500~-1500 fpm 범위"],
  ["APPROACH", "0.06", "접근 — 사고 빈발 구간, 민감도 ↑"],
  ["LANDING", "0.06", "착륙 — 최저 고도, 민감도 ↑"],
], [2160, 2400, 4800]));

children.push(p("학습 데이터는 Kaggle 비행 feature로부터 silver-labeling을 한다. 각 행을 7개 단계 샘플로 synthesize하고, XGBClassifier phase classifier를 학습하여 라벨을 부여한다. 휴리스틱 분류기 대비 90.3% agreement를 달성했으며, 기존 단일 모델 대비 alert fatigue를 67% 감소시켰다."));

children.push(new Paragraph({ children: [new PageBreak()] }));

children.push(h2("5.3 Active Learning Loop"));
children.push(p("이상 탐지 모델은 배포 후에도 계속 진화해야 한다. P6 Sprint에서 Active Learning 자동 재학습 loop을 구축했다."));

children.push(h3("5단계 Flow"));
children.push(numberedP("API가 이상 탐지 시 AnomalyEvent에 alert_id 부여 → Redis stream 기록"));
children.push(numberedP("분석가가 대시보드에서 True Positive / False Positive / Uncertain 으로 라벨링 → data/analyst_feedback/feedback.jsonl append"));
children.push(numberedP("Airflow DAG 매일 02:00 UTC 실행 — 단계별 FP rate 계산"));
children.push(numberedP("FP rate > 35% → contamination 하향 조정, FP rate < 10% → 상향 조정 (± 20% step, clip [0.01, 0.10])"));
children.push(numberedP("Per-phase IF 재학습 + data/models/.reload_signal touch → 서빙 ModelStore mtime watch로 hot-reload (서비스 재시작 불필요)"));

children.push(h3("Bandit v2 (P7-C)"));
children.push(p("P7 Sprint에서 uncertainty sampling에 Thompson sampling을 추가했다. 각 anomaly_type에 대해 Beta(1+TP, 1+FP) 분포로 posterior uncertainty를 sampling하고, (type, phase) 라운드로빈으로 다양성을 확보하여 분석가 라벨링 queue의 homogeneity를 해소했다."));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ══════════ 6. LLM ══════════
children.push(h1("6. LLM — AI 어시스턴트"));

children.push(h2("6.1 Qwen2.5-7B 선택 이유"));
children.push(p("LLM 베이스 모델로 Qwen2.5-7B-Instruct (Alibaba, 2024)를 선택했다. 7B 파라미터 instruction-tuned 모델로, Apache 2.0 오픈소스이며 총 18조 토큰으로 사전학습되었다."));

children.push(h3("대안 비교"));
children.push(simpleTable([
  ["대안", "선택하지 않은 이유"],
  ["Llama-3-8B", "영어 성능은 비슷하나 한국어 품질 열세. ATC 한국어 용어 정확도 중요"],
  ["Gemini / GPT-4", "클라우드 API. 항공 안전 데이터 외부 전송 금지. On-premise 배포 불가"],
  ["Qwen 72B", "72B는 RTX 3070 (8GB) 에 적재 불가. 7B 는 AWQ 4-bit로 40 tok/s 가능"],
  ["Mistral-7B", "KMMLU, KoBEST 한국어 벤치마크에서 Qwen 우세"],
  ["HyperCLOVA", "유료 API, On-premise 불가"],
  ["KoGPT 2.0", "2024년 이후 업데이트 없음, maintenance 우려"],
], [2160, 7200]));

children.push(h2("6.2 QLoRA 4-bit Fine-tuning"));
children.push(p("7B 모델의 full fine-tuning은 약 60GB VRAM을 요구한다. QLoRA(Dettmers et al., NeurIPS 2023)는 이를 6GB 수준으로 축소하여 홈 GPU (RTX 3070 8GB) 에서 학습 가능하게 만든다."));

children.push(h3("3단계 메커니즘"));
children.push(richP([
  { text: "① 4-bit Quantization — ", bold: true },
  "Base model 가중치를 FP16에서 NF4 (4-bit NormalFloat) 로 압축. 메모리 16배 절감. NF4는 정규분포 가정 하에 최적 양자화 수준으로 설계됨.",
]));
children.push(richP([
  { text: "② LoRA Adapter — ", bold: true },
  "원본 가중치는 frozen, Low-Rank Adapter 행렬만 학습 (rank=64). 학습 파라미터는 원본의 0.1% 수준. Hu et al. (ICLR 2022).",
]));
children.push(richP([
  { text: "③ Gradient Checkpointing — ", bold: true },
  "Forward pass 중간 결과 저장 대신 재계산. 메모리를 시간으로 trade-off하여 더 큰 배치 가능.",
]));

children.push(richP([
  { text: "학습 spec: ", bold: true, color: "1E88E5" },
  "RTX 3070 8GB · 9시간 · batch 4 · 13,969건 · TRL SFTTrainer. 결과 ",
  { text: "Train Loss 0.1053, Eval Token Accuracy 97.88%", bold: true, color: "00897B" },
]));

children.push(h2("6.3 DPO 선호도 학습"));
children.push(p("QLoRA로 SFT까지 완료한 모델은 \"정답\"은 학습했으나 \"선호되는 답변 스타일\"은 반영하지 못했다. 예: 영어와 한국어 코드스위칭, 공손어 누락 (\"~하시오\" 대신 \"~해라\")."));
children.push(p("DPO(Direct Preference Optimization, Rafailov et al., NeurIPS 2023 Best Paper)는 chosen/rejected pair만으로 학습한다. RLHF처럼 별도 Reward Model이 필요 없어 더 간단하고 안정적이다."));

children.push(h3("예시 (항공 도메인)"));
children.push(p("질문: \"윈드시어 감지 시 대응은?\""));
children.push(bullet("chosen: \"활주로 진입 대기, ATC 통보, 승객 안내. 필요 시 공항 변경 고려.\""));
children.push(bullet("rejected: \"Windshear detected. Follow the procedure.\""));

children.push(richP([
  { text: "학습 결과: ", bold: true, color: "1E88E5" },
  "Rewards Accuracy ",
  { text: "100%", bold: true, color: "00897B" },
  ", Eval Loss 0.02943. 한국어 출력 품질 체감상 대폭 개선.",
]));

children.push(h2("6.4 RAG + ChromaDB"));
children.push(p("LLM의 한계는 학습 시점 이후의 최신 정보를 모른다는 것이다. 최신 NOTAM, 공항별 SOP는 fine-tuning만으로 커버 불가능하다. RAG(Retrieval-Augmented Generation)는 외부 지식 베이스를 실시간 참조하여 이 한계를 극복한다."));

children.push(h3("4단계 Pipeline"));
children.push(numberedP("Query — 사용자 질문 (예: \"RKSI 활주로 15L 폐쇄 시 대응?\")"));
children.push(numberedP("Embed — BAAI/bge-m3 모델로 1024차원 벡터 변환"));
children.push(numberedP("Retrieve — ChromaDB 161 chunks 중 top-k=4 유사도 검색 (cosine similarity)"));
children.push(numberedP("Generate — Qwen2.5-7B + 검색 컨텍스트로 답변 생성"));

children.push(h3("ChromaDB 선택 이유"));
children.push(bullet("오픈소스 · 파이썬 우선 (vs Pinecone 유료, Weaviate 복잡)"));
children.push(bullet("임베디드 모드 (SQLite + Parquet) — 별도 서버 불필요"));
children.push(bullet("BAAI/bge-m3 임베딩 모델 — 다국어 지원 (한·영·중 동시), MTEB 벤치마크 상위"));

children.push(h3("코퍼스 구성 (161 chunks)"));
children.push(simpleTable([
  ["도메인", "chunks", "내용"],
  ["faa_aim", "26", "FAA Aeronautical Information Manual 요약"],
  ["icao_annex", "20", "ICAO Annex 2, 11, 14, 15"],
  ["sop", "25", "SkyOps 내부 SOP"],
  ["airport_ops", "21", "A-CDM 16 milestones, turnaround"],
  ["runbook", "18", "Incident response, model retrain, SWIM outage"],
  ["rksi_local", "15", "RKSI 활주로·도착·동절기 운영"],
  ["notam_samples", "13", "NOTAM 예시"],
  ["faa_ac", "12", "FAA AC 120-91 (Runway Safety), 120-92B (SMS)"],
  ["atc_procedure + 기타", "11", "ATC 절차, 규정"],
], [2880, 960, 5520]));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ══════════ 7. 서빙 ══════════
children.push(h1("7. 서빙 및 대시보드"));

children.push(h2("7.1 FastAPI + vLLM"));

children.push(h3("FastAPI 2.1.1"));
children.push(p("API 서버는 FastAPI를 채택했다. Flask 대비 주요 이점:"));
children.push(bullet("Pydantic v2 기반 자동 스키마 검증 — 잘못된 request는 400 에러 즉시 반환"));
children.push(bullet("Swagger UI 자동 생성 — /docs 엔드포인트에서 interactive 문서 즉시 이용 가능"));
children.push(bullet("async/await 네이티브 지원 — vLLM, Redis, DB 동시 호출 시 병목 없음"));
children.push(bullet("WebSocket first-class — 대시보드 실시간 push에 필수"));

children.push(p("P3 Sprint에서 ADR-001 Phase 1을 적용하여 1,120줄짜리 api.py 하나를 107줄 thin entry + 6개 router (gateway, delay, anomaly, rag, notification, streaming) 로 분리했다. 현재 15개 REST endpoint와 3개 WebSocket endpoint를 제공한다."));

children.push(h3("vLLM"));
children.push(p("LLM 추론 엔진으로 vLLM을 선택했다. HuggingFace Transformers 대비 주요 최적화:"));
children.push(richBullet([
  { text: "PagedAttention: ", bold: true },
  "GPU 메모리를 OS 페이징처럼 관리. Memory fragmentation 해소. Kwon et al. (SOSP 2023)",
]));
children.push(richBullet([
  { text: "Continuous Batching: ", bold: true },
  "서로 다른 길이 요청을 GPU 유휴 없이 처리",
]));
children.push(richBullet([
  { text: "AWQ 4-bit Quantization: ", bold: true },
  "모델 크기 4배 압축하면서 정확도 유지",
]));
children.push(richBullet([
  { text: "OpenAI 호환 API: ", bold: true },
  "기존 코드 수정 없이 drop-in replacement 가능",
]));

children.push(richP([
  { text: "성능 비교: ", bold: true, color: "1E88E5" },
  "RTX 3070에서 vLLM ",
  { text: "40 tok/s", bold: true, color: "00897B" },
  " vs Transformers 13 tok/s (약 3배 개선)",
]));

children.push(h2("7.2 Next.js 16 Dashboard"));
children.push(p("프론트엔드는 Next.js 16 App Router로 구성한 7개 페이지 관제 대시보드이다. TypeScript + Tailwind CSS 기반이며, 서버 컴포넌트 + 클라이언트 컴포넌트의 hybrid 구조를 활용한다."));

children.push(simpleTable([
  ["페이지", "경로", "주요 기능"],
  ["대시보드 개요", "/", "KPI 카드 4종 + 최근 알림 + 항공기 요약"],
  ["실시간 지도", "/map", "Leaflet 라이브맵 (WebSocket + SWR fallback)"],
  ["이상 탐지", "/anomaly", "실시간 알림 피드 + 심각도 필터 + AI 분석 버튼"],
  ["NOTAM 실시간", "/notam", "SWIM 실 데이터 + severity 필터 + 공항 분포"],
  ["지연 예측", "/predict", "폼 + XGBoost + Conformal interval 표시"],
  ["혼잡도 맵", "/heatmap", "MapLibre GL H3 R5 히트맵 (5초 갱신)"],
  ["AI 어시스턴트", "/chat", "RAG 채팅 + 시나리오 3종 + 승객 안내문"],
], [2160, 1680, 5520]));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ══════════ 8. MLOps ══════════
children.push(h1("8. MLOps & Engineering Package"));

children.push(h2("8.1 실험 관리 및 데이터 거버넌스"));
children.push(simpleTable([
  ["도구", "역할"],
  ["MLflow", "학습 run 추적 (hyperparameter, metrics, artifact). Experiment 버전 관리"],
  ["Airflow", "스케줄링 — 일 1회 재학습 DAG, Active Learning retrain (02:00 UTC)"],
  ["EvidentlyAI", "입력 분포 드리프트 감지 (Population Stability Index)"],
  ["Feast", "Feature Store. Offline parquet + Online Redis db=1. Training-serving skew 방지"],
  ["Apache Iceberg", "데이터 레이크 — Bronze/Silver/Gold 10 tables. Snapshot + time-travel"],
  ["OpenLineage + Marquez", "데이터셋 ↔ 모델 ↔ deployment lineage 그래프"],
  ["Confluent Schema Registry", "Avro 5 topics · BACKWARD compatibility 강제"],
], [3360, 6000]));

children.push(h2("8.2 관측성 스택"));
children.push(p("\"배포한 서비스가 실제로 건강한가\"를 측정하고 경보하는 5종 도구를 통합했다."));

children.push(simpleTable([
  ["도구", "역할"],
  ["Jaeger", "분산 trace. 요청 1건의 전 구간 (FastAPI → XGBoost → Redis) 추적"],
  ["Prometheus", "시계열 메트릭 수집 — QPS, latency, error rate. PromQL 쿼리"],
  ["Grafana", "9-panel SLO 대시보드 + 3개 alert rules (ErrorRate, Latency, Drift)"],
  ["OpenTelemetry", "계측 표준 — OTLP gRPC 방출. Datadog/New Relic 등 vendor 중립"],
  ["Marquez", "OpenLineage UI. 모델 learning run ↔ 입력 dataset 그래프"],
], [2400, 6960]));

children.push(h2("8.3 k8s + Helm + Terraform"));
children.push(p("배포 자동화를 위해 3계층 IaC 구조를 구축했다."));

children.push(h3("Helm Chart (k8s/helm/skyops/)"));
children.push(p("Chart 0.1.0, appVersion 2.1.2, 템플릿 6개. 환경별 values 파일 3개 (dev, staging, prod)로 feature flag 제어 (iceberg, feast, openlineage, canaryRollout, networkPolicy, hitlApproval). Pod Security Admission restricted profile 준수."));

children.push(h3("Terraform (terraform/)"));
children.push(p("GCP용 모듈 + 환경별 stack (dev, staging, prod). helm_release를 통해 Helm Chart 배포. ExternalSecrets로 GCP Secret Manager 연동."));

children.push(h3("Argo Rollouts (P7-F)"));
children.push(p("4-step canary deployment (5% → 25% → 50% → 100%) with Prometheus AnalysisTemplates. api-success-rate (5xx < 1%) + api-latency-p95 (p95 < 500ms) 2개 gate로 자동 promote/abort."));

children.push(h2("8.4 CI/CD + Supply-chain Security (P7-G, P8-G)"));
children.push(p("모든 릴리스 이미지는 공급망 보안 4가지 보장을 만족한다."));
children.push(numberedP("서명(signed): Sigstore cosign keyless via GitHub OIDC"));
children.push(numberedP("SBOM 첨부: SPDX-JSON + CycloneDX (syft, cosign attestation)"));
children.push(numberedP("취약점 스캔: Trivy CRITICAL/HIGH 0 findings"));
children.push(numberedP("Admission gate: Kyverno ClusterPolicy로 서명 미달성 pod 배포 거부"));

children.push(p("GitHub Actions release.yml이 tag push 시 자동 실행하여 multi-arch (linux/amd64 + linux/arm64) build + push + sign + attest를 수행한다."));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ══════════ 9. 성능 평가 ══════════
children.push(h1("9. 성능 평가"));

children.push(h2("9.1 지연 예측 (XGBoost)"));
children.push(simpleTable([
  ["지표", "P0 Baseline", "P1 최종", "변화율"],
  ["Val RMSE (분)", "24.60", "22.61", "-8.1%"],
  ["Test RMSE (분)", "36.52", "28.18", "-22.8%"],
  ["Test R²", "0.0996", "0.4328", "+335%"],
  ["Val R²", "0.0931", "0.3784", "+306%"],
  ["Delay Accuracy (Val)", "88.49%", "91.15%", "+2.66%p"],
  ["Delay Accuracy (Test)", "84.16%", "89.04%", "+4.88%p"],
  ["5-Fold CV RMSE std", "±6.14", "±1.51", "4배 안정"],
  ["Val-Test gap", "12분", "5.5분", "격차 절반"],
  ["Conformal coverage", "90.00%", "90.00%", "목표 달성"],
  ["Conformal width (split)", "38.74분", "30.84분", "-7.9분"],
], [3120, 2160, 2160, 1920]));

children.push(h2("9.2 이상 탐지"));
children.push(simpleTable([
  ["지표", "값"],
  ["F1 Score (baseline IF)", "0.345 (label 품질 제약)"],
  ["ML Phase classifier agreement", "90.3% (vs heuristic)"],
  ["Per-phase IF 수", "7 (TAXI~LANDING)"],
  ["Contamination 범위", "0.02 (TAXI) ~ 0.06 (APPROACH/LANDING)"],
  ["Alert fatigue 감소", "67% (단일 모델 대비)"],
  ["Active Learning 주기", "매일 02:00 UTC"],
], [4800, 4560]));

children.push(h2("9.3 LLM + RAG"));
children.push(simpleTable([
  ["지표", "값"],
  ["QLoRA Train Loss", "0.1053"],
  ["Eval Token Accuracy", "97.88%"],
  ["DPO Eval Loss", "0.02943"],
  ["DPO Rewards Accuracy", "100%"],
  ["ROUGE-L", "0.169"],
  ["BLEU-1", "0.121"],
  ["RAG chunks (초기 → 최종)", "6 → 161 (+2,583%)"],
  ["Korean SFT/DPO 시드 생성", "3,000 + 500 pairs"],
  ["Embedding 모델", "BAAI/bge-m3 (1024차원, multilingual)"],
], [4800, 4560]));

children.push(h2("9.4 데이터 통합"));
children.push(simpleTable([
  ["소스", "상태"],
  ["OpenSky ADS-B", "✓ 실시간 10초 polling"],
  ["NOAA/KMA METAR", "✓ 실시간 30분 polling"],
  ["FAA SWIM NOTAM", "✓ 실연동 (60초 219건 검증)"],
  ["KAC ACDM", "○ Client 준비 (Service Key 발급 시 활성)"],
  ["EUROCONTROL NM B2B", "△ 미구현 (credentials 필요)"],
], [3840, 5520]));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ══════════ 10. 한계 및 향후 계획 ══════════
children.push(h1("10. 한계 및 향후 계획"));

children.push(h2("10.1 한계"));

children.push(h3("데이터 측면"));
children.push(bullet("학습 데이터가 Kaggle US 국내선 13,969건. 한국 공항 특성 (RKSI 북풍 flow, 동절기 de-icing 등) 미반영"));
children.push(bullet("실 ground truth label 부족. Isolation Forest F1 0.345는 pseudo-label 기반이므로 실제 성능과 차이 가능성"));

children.push(h3("모델 측면"));
children.push(bullet("LLM Korean SFT/DPO 시드 3,500건 생성했으나 실제 재학습 미실시 (GPU 시간 필요)"));
children.push(bullet("vLLM 현재 RTX 3070 단일 GPU 40 tok/s. 실 운영은 100+ tok/s 필요 (tensor parallelism 적용 예정)"));

children.push(h3("인프라 측면"));
children.push(bullet("ADR-003 Multi-region deployment는 Proposed 상태. 실 GCP GKE 배포 미완"));
children.push(bullet("EUROCONTROL NM B2B credentials 미보유. ATFM 실시간 CTOT 데이터 없음"));
children.push(bullet("현재 Synology NAS 기반 임시 배포. 프로덕션 SLA 미충족"));

children.push(h2("10.2 향후 계획 (P9+)"));
children.push(numberedP("한국공항공사 MOU 추진 → 국내 공항 운항 데이터 확보 → XGBoost 국내 재학습"));
children.push(numberedP("Active Learning 실운영 데이터 3개월 누적 → IF F1 목표 0.85+ 달성"));
children.push(numberedP("Qwen2.5 + Korean SFT/DPO 재학습 (멀티 GPU) + vLLM tensor parallelism"));
children.push(numberedP("EUROCONTROL NM B2B 계약 추진 → ATFM 실시간 CTOT 통합"));
children.push(numberedP("GCP GKE Phase A 배포 → Cloud Run 운영 → ADR-003 Multi-region Phase B/C"));
children.push(numberedP("Kyverno ClusterPolicy로 서명된 이미지만 admission → 공급망 전면 강제"));
children.push(numberedP("ICAO Annex 10 인증 + RTCA DO-178C 소프트웨어 인증 + NIST AI RMF 준수 단계적 추진"));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ══════════ 11. 결론 ══════════
children.push(h1("11. 결론"));

children.push(p("SkyOps Intelligence는 \"항공 AI 데모\"가 아니라 \"공항·항공사 운영의 Disruption Intelligence Copilot\"을 지향하며 설계되었다. 본 프로젝트의 5대 기여는 다음과 같다."));

children.push(h3("(1) 불확실성 정량화를 통한 의사결정 지원"));
children.push(p("Conformal Prediction 기법으로 분포 가정 없이 유효 예측구간을 제공. Test R² 0.4328에 더해 empirical coverage 90.00%를 달성하여 관제사가 정량적 위험 판단 가능한 수준."));

children.push(h3("(2) 도메인 지식과 ML의 결합"));
children.push(p("Rotation features 5종 추가만으로 Test R² 0.10 → 0.43 (+335%). 모델을 키우는 것보다 도메인 지식이 결정적임을 실증."));

children.push(h3("(3) Alert Fatigue 해결"));
children.push(p("Per-phase IF ×7 + Active Learning 자동 재학습 loop으로 관제사가 정말 봐야 할 이상만 상위에 노출. 67% alert fatigue 감소."));

children.push(h3("(4) 프로덕션 데이터 통합"));
children.push(p("미 FAA의 공식 System Wide Information Management 직접 연동. Solace SMF/TLS + AIXM 5.1 파싱으로 실 NOTAM 219건/60초 수신 검증."));

children.push(h3("(5) Engineering Package 완성도"));
children.push(p("MLflow, Airflow, Feast, Iceberg, OpenLineage, Marquez, Prometheus, Grafana, Jaeger, Argo Rollouts, Cosign, SBOM, Terraform, Helm을 통합한 엔터프라이즈급 인프라. 3 ADR, 7 Runbook, 564줄 Reproduction Guide."));

children.push(p(""));
children.push(quote("본 프로젝트는 대학 캡스톤의 \"학습된 모델\" 단계에서 실무급 \"운영 가능한 제품\"으로 체급을 전환한 사례이다. 2일 만에 진행한 P0~P8 Sprint는 엔지니어링 품질의 근본적 업그레이드가 단시간에도 가능함을 보여주며, 이는 향후 산업계 진입 시 즉시 기여 가능한 역량의 증거이다."));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ══════════ 12. 참고문헌 ══════════
children.push(h1("12. 참고문헌"));

const refs = [
  "Chen, T., & Guestrin, C. (2016). XGBoost: A Scalable Tree Boosting System. KDD '16.",
  "Liu, F. T., Ting, K. M., & Zhou, Z.-H. (2008). Isolation Forest. ICDM '08.",
  "Vovk, V., Gammerman, A., & Shafer, G. (2005). Algorithmic Learning in a Random World. Springer.",
  "Romano, Y., Patterson, E., & Candès, E. (2019). Conformalized Quantile Regression. NeurIPS '19.",
  "Dettmers, T., Pagnoni, A., Holtzman, A., & Zettlemoyer, L. (2023). QLoRA: Efficient Finetuning of Quantized LLMs. NeurIPS '23.",
  "Hu, E. J., et al. (2022). LoRA: Low-Rank Adaptation of Large Language Models. ICLR '22.",
  "Rafailov, R., et al. (2023). Direct Preference Optimization: Your Language Model is Secretly a Reward Model. NeurIPS '23.",
  "Kwon, W., et al. (2023). Efficient Memory Management for Large Language Model Serving with PagedAttention. SOSP '23.",
  "Lewis, P., et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS '20.",
  "EUROCONTROL (2019). CODA Digest Q2 2019: Reactionary Delay Analysis.",
  "FAA (2024). System Wide Information Management (SWIM) Program Overview.",
  "ICAO (2018). Annex 15: Aeronautical Information Services (15th edition).",
  "ICAO Doc 9859 (2018). Safety Management Manual (4th edition).",
  "NIST AI Risk Management Framework (AI RMF 1.0), January 2023.",
  "Es, S., et al. (2023). RAGAs: Automated Evaluation of Retrieval Augmented Generation. arXiv:2309.15217.",
];
refs.forEach((ref, i) => {
  children.push(new Paragraph({
    indent: { left: 400, hanging: 400 },
    spacing: { line: 320, after: 80 },
    children: [new TextRun({ text: `[${i + 1}] ${ref}`, font: FONT, size: 20 })],
  }));
});

// 부록
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h1("부록 A. 핵심 Git Commit 이력 (P0~P8)"));

const commits = [
  ["Sprint", "Commits", "핵심 변경"],
  ["P0", "b5b41c3", "TimeSeriesSplit 전환 — CV std ±0.30→±6.14"],
  ["P1", "2863be8, cb3798c", "Conformal + Event Model + Rotation features (R² +335%)"],
  ["P2", "3451269, df50fca, 887bf1e", "ADR-001 + RAGAs + Phase-aware anomaly"],
  ["P3", "e00a10b, 5e32ee5, 99807fc", "Dashboard re-write + OTel + Router 분리 + AL"],
  ["P4+", "8a3ac43~c7c3cf6 (7건)", "Packaging + ADR-002 + ChromaDB 95 + CQR + Docker/k8s/CI"],
  ["P5+", "4249820~7189a24 (8건)", "FAA SWIM + ML phase + Per-phase IF + Jaeger + Reproduction"],
  ["P6", "69bfa9c~1ee975b (9건)", "Feast + Avro SR + AL loop + Iceberg + Prometheus/Grafana + 161 chunks"],
  ["P7", "bfafa8a~95ad56a (9건)", "Iceberg writers + OpenLineage + Bandit + KR SFT + KAC + Argo Rollouts"],
  ["P8", "6d47f62~62b41b3 (10건)", "NAS + Helm + Terraform + Evidence + Audit + HITL + Cosign + DR"],
];
children.push(simpleTable(commits, [1200, 2640, 5520]));

children.push(h1("부록 B. 주요 문서"));
children.push(bullet("README.md — 프로젝트 최상위 소개 (623 라인)"));
children.push(bullet("docs/reproduction_guide.md — 전체 재현 가이드 (564 라인)"));
children.push(bullet("docs/event_model.md — 7 Canonical Events Avro schema v2.0"));
children.push(bullet("docs/performance_benchmark.md — 실측 성능 지표"));
children.push(bullet("docs/limitations_and_improvements.md — 한계 및 개선 로드맵"));
children.push(bullet("docs/policy_proposal.md — 항공사·공항 도입 3단계 방안"));
children.push(bullet("docs/adr/ADR-001-service-decomposition.md — Service Decomposition"));
children.push(bullet("docs/adr/ADR-002-api-gateway-selection.md — Traefik v3"));
children.push(bullet("docs/adr/ADR-003-multi-region-deployment.md — Hybrid KR primary + EU/US read"));
children.push(bullet("docs/runbooks/incident_playbook.md — P1~P4 Severity 대응"));
children.push(bullet("docs/runbooks/dr_drill.sh — ADR-003 Failover 자동화"));
children.push(bullet("docs/runbooks/secret_rotation.md — 비밀 교체 playbook"));
children.push(bullet("docs/runbooks/supply_chain.md — cosign + SBOM + Kyverno"));
children.push(bullet("docs/evidence/README.md — 5종 재현 가능 증거 패키지"));

children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 800 },
  children: [new TextRun({ text: "— 끝 —", font: FONT, size: 24, color: "78909C" })],
}));

// ─────────────────────────────────────────────────────
// Document 생성
// ─────────────────────────────────────────────────────
const doc = new Document({
  creator: "DoubleJ 정재원",
  title: "SkyOps Intelligence 최종 보고서",
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: FONT, color: "1E3A5F" },
        paragraph: { spacing: { before: 360, after: 240 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: FONT, color: "1E88E5" },
        paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, font: FONT, color: "263238" },
        paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },  // A4
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ text: "SkyOps Intelligence · 최종 보고서", font: FONT, size: 18, color: "78909C" })],
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ text: "- ", font: FONT, size: 18, color: "78909C" }),
            new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18, color: "78909C" }),
            new TextRun({ text: " -", font: FONT, size: 18, color: "78909C" }),
          ],
        })],
      }),
    },
    children,
  }],
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("SkyOps_Intelligence_최종보고서.docx", buffer);
  console.log("✅ DOCX 생성 완료");
}).catch(err => {
  console.error("❌ 오류:", err);
  process.exit(1);
});
