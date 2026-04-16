// SkyOps Intelligence — 발표용 PPTX 생성 스크립트
// 실행: node build_pptx.js

const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";  // 10" × 5.625"
pres.author = "DoubleJ / 정재원";
pres.title = "SkyOps Intelligence — 실시간 항공 운항 AI 플랫폼";
pres.company = "빅데이터과 캡스톤디자인";

// ─────────────────────────────────────────────────────────────
// 색상 팔레트 (Midnight Aviation)
// ─────────────────────────────────────────────────────────────
const C = {
  navy:      "0B1F3A",   // 메인 다크 (하늘의 깊은 색)
  skyBlue:   "1E88E5",   // 액센트
  ice:       "E3F2FD",   // 밝은 배경
  amber:     "FFB300",   // 경고/강조
  coral:     "EF5350",   // 핫 강조
  teal:      "00897B",   // 성공/데이터
  slate:     "37474F",   // 본문
  mute:      "78909C",   // 캡션
  cream:     "FAFAFA",   // 슬라이드 배경
  white:     "FFFFFF",
};

const FONT_T = "Malgun Gothic";   // 헤더 (맑은 고딕)
const FONT_B = "Malgun Gothic";   // 본문

// ─────────────────────────────────────────────────────────────
// 공통 헬퍼
// ─────────────────────────────────────────────────────────────
function addFooter(slide, pageNum, total) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 5.35, w: 10, h: 0.28, fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText("SkyOps Intelligence · 2026-04-16", {
    x: 0.3, y: 5.37, w: 5, h: 0.24, fontSize: 9, color: C.ice, fontFace: FONT_B, margin: 0
  });
  slide.addText(`${pageNum} / ${total}`, {
    x: 9.0, y: 5.37, w: 0.8, h: 0.24, fontSize: 9, color: C.ice, fontFace: FONT_B,
    align: "right", margin: 0
  });
}

function addHeader(slide, chapterTag, title) {
  // 상단 타이틀 배경
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.75, fill: { color: C.cream }, line: { color: C.cream }
  });
  // 좌측 챕터 태그
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.3, y: 0.15, w: 0.08, h: 0.45, fill: { color: C.skyBlue }, line: { color: C.skyBlue }
  });
  slide.addText(chapterTag, {
    x: 0.5, y: 0.15, w: 4, h: 0.2, fontSize: 9, color: C.mute, fontFace: FONT_B,
    charSpacing: 4, margin: 0
  });
  slide.addText(title, {
    x: 0.5, y: 0.32, w: 9.2, h: 0.45, fontSize: 22, bold: true, color: C.navy, fontFace: FONT_T, margin: 0
  });
}

function addIconBullet(slide, x, y, w, h, icon, title, body) {
  // 아이콘 원
  slide.addShape(pres.shapes.OVAL, {
    x, y, w: 0.45, h: 0.45, fill: { color: C.skyBlue }, line: { color: C.skyBlue }
  });
  slide.addText(icon, {
    x, y, w: 0.45, h: 0.45, fontSize: 18, color: C.white, fontFace: FONT_T,
    align: "center", valign: "middle", bold: true, margin: 0
  });
  // 타이틀
  slide.addText(title, {
    x: x + 0.6, y, w: w - 0.6, h: 0.3,
    fontSize: 14, bold: true, color: C.navy, fontFace: FONT_T, margin: 0
  });
  // 본문
  slide.addText(body, {
    x: x + 0.6, y: y + 0.3, w: w - 0.6, h: h - 0.3,
    fontSize: 11, color: C.slate, fontFace: FONT_B, margin: 0
  });
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 1 · 표지
// ─────────────────────────────────────────────────────────────
const TOTAL = 28;  // 예정 슬라이드 수

{
  const s = pres.addSlide();
  s.background = { color: C.navy };
  // 액센트 라인 (좌측)
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.2, h: 5.625, fill: { color: C.skyBlue }, line: { color: C.skyBlue }
  });
  // 로고 텍스트
  s.addText("✈ SkyOps", {
    x: 0.7, y: 0.5, w: 5, h: 0.6, fontSize: 32, bold: true, color: C.skyBlue, fontFace: FONT_T, margin: 0
  });
  // 메인 타이틀
  s.addText("SkyOps Intelligence", {
    x: 0.7, y: 1.6, w: 9, h: 0.9, fontSize: 48, bold: true, color: C.white, fontFace: FONT_T, margin: 0
  });
  s.addText("실시간 항공 운항 이상 탐지 및 AI 관제 보조 플랫폼", {
    x: 0.7, y: 2.55, w: 9, h: 0.5, fontSize: 20, color: C.ice, fontFace: FONT_T, margin: 0
  });
  // 한 줄 요약
  s.addText("「이상을 탐지하고, 원인을 설명하고, 대응 절차를 5초 이내에 자동 생성합니다」", {
    x: 0.7, y: 3.2, w: 9, h: 0.4, fontSize: 14, italic: true, color: C.amber, fontFace: FONT_B, margin: 0
  });
  // 하단 정보
  s.addText([
    { text: "발표자 ", options: { color: C.mute, fontSize: 12 } },
    { text: "정재원 ", options: { color: C.white, fontSize: 12, bold: true } },
    { text: "  ·  지도교수 ", options: { color: C.mute, fontSize: 12 } },
    { text: "조상구 교수님", options: { color: C.white, fontSize: 12, bold: true } },
  ], { x: 0.7, y: 4.5, w: 9, h: 0.3, margin: 0 });
  s.addText("2026학년도 1학기 캡스톤디자인 최종 발표 · 빅데이터과 · DoubleJ팀", {
    x: 0.7, y: 4.85, w: 9, h: 0.3, fontSize: 11, color: C.mute, fontFace: FONT_B, margin: 0
  });
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 2 · 목차
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "목차 · CONTENTS", "발표 순서");

  const items = [
    ["01", "프로젝트 소개", "왜 만들었는가, 무엇을 해결하는가"],
    ["02", "시스템 아키텍처", "5-Layer 구조와 데이터 흐름"],
    ["03", "데이터 수집 파이프라인", "Kafka · OpenSky · FAA SWIM · METAR"],
    ["04", "ML 모델 · 지연 예측", "XGBoost + Conformal Prediction"],
    ["05", "ML 모델 · 이상 탐지", "Per-phase Isolation Forest + Active Learning"],
    ["06", "LLM · AI 어시스턴트", "Qwen2.5-7B + QLoRA + DPO + RAG"],
    ["07", "서빙 · 대시보드", "FastAPI 13 endpoints + Next.js 16"],
    ["08", "MLOps & Engineering Package", "Observability + Data Governance + IaC"],
    ["09", "성능 지표 & 진화 과정", "P0 → P8 roadmap"],
    ["10", "시연 & 한계 · Q&A", "실제 동작 + 향후 계획"],
  ];

  items.forEach((it, i) => {
    const y = 1.0 + i * 0.42;
    // 번호
    s.addText(it[0], {
      x: 0.5, y, w: 0.6, h: 0.38, fontSize: 14, bold: true, color: C.skyBlue,
      fontFace: FONT_T, margin: 0
    });
    // 제목
    s.addText(it[1], {
      x: 1.2, y, w: 3.8, h: 0.38, fontSize: 13, bold: true, color: C.navy,
      fontFace: FONT_T, margin: 0
    });
    // 설명
    s.addText(it[2], {
      x: 5.0, y, w: 4.5, h: 0.38, fontSize: 11, color: C.slate,
      fontFace: FONT_B, margin: 0
    });
  });

  addFooter(s, 2, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 3 · 프로젝트 개요
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 01 · 프로젝트 소개", "한 줄 요약");

  // 큰 인용구
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.0, w: 9, h: 1.2, fill: { color: C.navy }, line: { color: C.navy }
  });
  s.addText("「항공 관제사를 위한 실시간 AI 파트너」", {
    x: 0.5, y: 1.1, w: 9, h: 0.5, fontSize: 26, bold: true, color: C.white,
    fontFace: FONT_T, align: "center", valign: "middle", margin: 0
  });
  s.addText("이상 탐지 → 원인 자연어 설명 → 대응 절차 자동 생성, 5초 이내", {
    x: 0.5, y: 1.60, w: 9, h: 0.45, fontSize: 14, color: C.amber, italic: true,
    fontFace: FONT_T, align: "center", valign: "middle", margin: 0
  });

  // 6대 핵심 기능 (2x3 grid)
  const features = [
    ["①", "15분 선행 지연 예측", "XGBoost + Conformal — 예측값 + 90% 신뢰구간"],
    ["②", "실시간 이상 탐지", "비행 단계별 Isolation Forest ×7 + 자동 학습"],
    ["③", "자연어 원인 설명", "QLoRA+DPO 파인튜닝 한국어 LLM + RAG 161 chunks"],
    ["④", "실시간 NOTAM 통합", "FAA SWIM 실연동 (60초에 219건 검증)"],
    ["⑤", "관제 대시보드", "Next.js 16 · 7 페이지 · 실시간 지도/히트맵"],
    ["⑥", "승객 안내문 자동", "지연 유형별 안내방송문 생성 + 승인 흐름"],
  ];
  features.forEach((f, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = 0.5 + col * 3.0;
    const y = 2.5 + row * 1.2;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 2.85, h: 1.05, fill: { color: C.white }, line: { color: C.ice, width: 1 }
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 0.05, h: 1.05, fill: { color: C.skyBlue }, line: { color: C.skyBlue }
    });
    s.addText(f[0] + " " + f[1], {
      x: x + 0.15, y: y + 0.1, w: 2.6, h: 0.3, fontSize: 11, bold: true, color: C.navy,
      fontFace: FONT_T, margin: 0
    });
    s.addText(f[2], {
      x: x + 0.15, y: y + 0.40, w: 2.6, h: 0.62, fontSize: 9, color: C.slate,
      fontFace: FONT_B, margin: 0
    });
  });

  addFooter(s, 3, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 4 · 문제 정의
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 01 · 프로젝트 소개", "왜 항공 운항 AI 인가?");

  // 좌측: 문제
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.0, w: 4.4, h: 3.9, fill: { color: C.white }, line: { color: C.ice, width: 1 }
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.0, w: 4.4, h: 0.5, fill: { color: C.coral }, line: { color: C.coral }
  });
  s.addText("현재 항공 운영의 3대 문제", {
    x: 0.65, y: 1.05, w: 4.1, h: 0.4, fontSize: 14, bold: true, color: C.white,
    fontFace: FONT_T, margin: 0
  });

  const problems = [
    ["지연 예측 불투명", "「얼마나 늦어질지」는 예측되지만 「얼마나 확신 가능한지」는 없음. 관제사는 \"예상 15분 지연\"만 보고 결정해야 함."],
    ["이상 탐지 false positive 과다", "단일 임계값 Rule 로는 이륙 중 정상적 급상승도 이상으로 오탐. 알람 피로(alert fatigue) 심각."],
    ["의사결정 보조 부재", "규정·NOTAM·SOP 가 수백 페이지. 비상 시 즉시 참조 불가. 경험 많은 관제사에게만 의존."],
  ];
  problems.forEach((p, i) => {
    const y = 1.65 + i * 1.05;
    s.addText("❗ " + p[0], {
      x: 0.7, y, w: 4.0, h: 0.3, fontSize: 12, bold: true, color: C.coral,
      fontFace: FONT_T, margin: 0
    });
    s.addText(p[1], {
      x: 0.7, y: y + 0.3, w: 4.0, h: 0.7, fontSize: 10, color: C.slate,
      fontFace: FONT_B, margin: 0
    });
  });

  // 우측: 우리 접근
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 1.0, w: 4.4, h: 3.9, fill: { color: C.white }, line: { color: C.ice, width: 1 }
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 1.0, w: 4.4, h: 0.5, fill: { color: C.teal }, line: { color: C.teal }
  });
  s.addText("SkyOps 의 해결 접근", {
    x: 5.25, y: 1.05, w: 4.1, h: 0.4, fontSize: 14, bold: true, color: C.white,
    fontFace: FONT_T, margin: 0
  });

  const solutions = [
    ["확률적 예측", "Conformal Prediction 으로 「90% 확률로 6~41분 지연」 형태의 신뢰구간 제공 → 관제사가 위험 감수 정도를 정량적으로 판단"],
    ["Phase-aware 탐지", "비행 단계(이착륙·순항·접근) 별로 별도 IF 모델 ×7 + Active Learning → alert fatigue 67% 감소"],
    ["AI 어시스턴트", "한국어 특화 LLM + RAG 가 규정·SOP 에서 해당 절차를 자동 추출. 5초 이내 자연어 설명 + 승객 안내문 생성"],
  ];
  solutions.forEach((p, i) => {
    const y = 1.65 + i * 1.05;
    s.addText("✓ " + p[0], {
      x: 5.3, y, w: 4.0, h: 0.3, fontSize: 12, bold: true, color: C.teal,
      fontFace: FONT_T, margin: 0
    });
    s.addText(p[1], {
      x: 5.3, y: y + 0.3, w: 4.0, h: 0.7, fontSize: 10, color: C.slate,
      fontFace: FONT_B, margin: 0
    });
  });

  addFooter(s, 4, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 5 · 시스템 아키텍처 개요
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 02 · 시스템 아키텍처", "5-Layer 구조");

  const layers = [
    ["Layer 1", "데이터 수집", "OpenSky ADS-B · NOAA METAR · FAA SWIM · KAC 공공데이터", C.skyBlue],
    ["Layer 2", "스트리밍 처리", "Apache Kafka + Avro Schema Registry → PyFlink → Redis", C.teal],
    ["Layer 3", "AI 모델", "XGBoost (지연) · Per-phase IF ×7 (이상) · Qwen2.5-7B (LLM)", C.amber],
    ["Layer 4", "서빙", "FastAPI 15 endpoints + vLLM AWQ + ChromaDB RAG", C.coral],
    ["Layer 5", "대시보드", "Next.js 16 · 7 페이지 · Leaflet 지도 + Cloudflare Tunnel", C.navy],
  ];
  layers.forEach((l, i) => {
    const y = 1.0 + i * 0.83;
    // 레이어 태그
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y, w: 1.3, h: 0.72, fill: { color: l[3] }, line: { color: l[3] }
    });
    s.addText(l[0], {
      x: 0.5, y: y + 0.08, w: 1.3, h: 0.25, fontSize: 11, bold: true, color: C.white,
      fontFace: FONT_T, align: "center", margin: 0
    });
    s.addText(l[1], {
      x: 0.5, y: y + 0.35, w: 1.3, h: 0.3, fontSize: 10, color: C.white,
      fontFace: FONT_T, align: "center", margin: 0
    });
    // 내용
    s.addShape(pres.shapes.RECTANGLE, {
      x: 1.9, y, w: 7.6, h: 0.72, fill: { color: C.white }, line: { color: C.ice, width: 1 }
    });
    s.addText(l[2], {
      x: 2.0, y: y + 0.05, w: 7.5, h: 0.62, fontSize: 11, color: C.slate,
      fontFace: FONT_B, valign: "middle", margin: 0
    });
    // 화살표 (마지막 제외)
    if (i < layers.length - 1) {
      s.addText("↓", {
        x: 1.05, y: y + 0.72, w: 0.3, h: 0.13, fontSize: 12, color: C.mute,
        fontFace: FONT_T, align: "center", margin: 0
      });
    }
  });

  addFooter(s, 5, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 6 · 데이터 소스
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 03 · 데이터 수집", "4가지 실시간 데이터 소스");

  const sources = [
    {
      name: "OpenSky Network",
      sub: "ADS-B 비행 위치",
      what: "공개 API, 유럽·아시아 커버리지",
      why: "실제 항공기 위치 (위도·경도·고도·속도) 를 10초 주기로 수집. 전 세계 약 35,000개 지상 수신기에서 익명 기여.",
      use: "비행 경로 추적, 실시간 지도, 이상 탐지의 물리적 feature 입력",
      color: C.skyBlue,
    },
    {
      name: "NOAA / KMA METAR",
      sub: "실시간 기상 관측",
      what: "30분마다 세계 공항 기상 보고",
      why: "기상(바람·시정·운고·기온) 은 지연의 가장 큰 단일 원인. METAR 는 국제 표준 포맷.",
      use: "XGBoost 지연 예측 feature, 기상 기반 GDP 감지",
      color: C.teal,
    },
    {
      name: "FAA SWIM",
      sub: "NOTAM 실시간 피드 🔥",
      what: "Solace JMS over SMF/TLS (프로덕션급)",
      why: "미 FAA 의 공식 System Wide Information Management. 활주로 폐쇄·항법시설 장애 등 운항 안전 공지.",
      use: "실시간 NOTAM 통합 (60초에 219건 수신 검증 완료)",
      color: C.amber,
    },
    {
      name: "한국공항공사 ACDM",
      sub: "공공데이터포털 API",
      what: "인천·김포 운항정보",
      why: "한국 공항 specific 데이터. EUROCONTROL NM B2B 계약 없이도 한국 trafffic 활용 가능한 대안.",
      use: "한국 ATFM 지연 상황 inference (GDP · CTOT 추정)",
      color: C.coral,
    },
  ];
  sources.forEach((src, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.4 + col * 4.75;
    const y = 1.0 + row * 2.1;

    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 4.6, h: 1.95, fill: { color: C.white }, line: { color: C.ice, width: 1 }
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 0.1, h: 1.95, fill: { color: src.color }, line: { color: src.color }
    });
    s.addText(src.name, {
      x: x + 0.2, y: y + 0.1, w: 4.3, h: 0.3, fontSize: 13, bold: true, color: C.navy,
      fontFace: FONT_T, margin: 0
    });
    s.addText(src.sub, {
      x: x + 0.2, y: y + 0.35, w: 4.3, h: 0.25, fontSize: 10, color: src.color,
      fontFace: FONT_T, bold: true, margin: 0
    });
    s.addText([
      { text: "▶ ", options: { color: src.color, bold: true } },
      { text: src.what, options: { color: C.slate, fontSize: 9 } },
    ], { x: x + 0.2, y: y + 0.65, w: 4.3, h: 0.25, fontSize: 9, fontFace: FONT_B, margin: 0 });
    s.addText(src.why, {
      x: x + 0.2, y: y + 0.9, w: 4.3, h: 0.6, fontSize: 9, color: C.slate,
      fontFace: FONT_B, margin: 0
    });
    s.addText([
      { text: "사용처  ", options: { color: src.color, bold: true, fontSize: 9 } },
      { text: src.use, options: { color: C.slate, fontSize: 9 } },
    ], { x: x + 0.2, y: y + 1.55, w: 4.3, h: 0.35, fontFace: FONT_B, margin: 0 });
  });

  addFooter(s, 6, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 7 · Kafka 스트리밍
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 03 · 데이터 수집", "Apache Kafka — 왜 썼나?");

  // 좌측: 왜 Kafka
  s.addText("💡 왜 Kafka 인가?", {
    x: 0.5, y: 1.0, w: 4.5, h: 0.4, fontSize: 16, bold: true, color: C.navy,
    fontFace: FONT_T, margin: 0
  });
  const whys = [
    "항공 데이터는 초당 수천 건 (ADS-B) — HTTP REST 로는 backpressure 감당 불가. Kafka 의 pub-sub + 로그 저장 모델이 적합.",
    "이상 탐지·지연 예측·시각화가 모두 같은 데이터를 소비해야 함. Kafka 는 하나의 producer → 여러 consumer 를 효율적으로 지원.",
    "시스템 실패 시 재처리(replay) 필수. Kafka 의 offset + 로그 기반 저장으로 「어제 14시부터 다시 읽기」 가능.",
    "Schema Registry (Avro) 와 결합하면 producer/consumer 간 계약 강제 → 필드 잘못 보내면 즉시 reject.",
  ];
  whys.forEach((why, i) => {
    const y = 1.5 + i * 0.75;
    s.addShape(pres.shapes.OVAL, {
      x: 0.5, y: y + 0.05, w: 0.25, h: 0.25, fill: { color: C.skyBlue }, line: { color: C.skyBlue }
    });
    s.addText(`${i + 1}`, {
      x: 0.5, y: y + 0.05, w: 0.25, h: 0.25, fontSize: 10, bold: true, color: C.white,
      fontFace: FONT_T, align: "center", valign: "middle", margin: 0
    });
    s.addText(why, {
      x: 0.85, y, w: 4.2, h: 0.7, fontSize: 10, color: C.slate, fontFace: FONT_B, margin: 0
    });
  });

  // 우측: Topic 구성
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.3, y: 1.0, w: 4.2, h: 3.9, fill: { color: C.navy }, line: { color: C.navy }
  });
  s.addText("📡 Kafka Topics (6개 · Avro v2.0)", {
    x: 5.5, y: 1.1, w: 4.0, h: 0.3, fontSize: 13, bold: true, color: C.amber,
    fontFace: FONT_T, margin: 0
  });
  const topics = [
    ["flight-position", "ADS-B 비행 위치 · 10초 단위"],
    ["weather-event", "METAR/TAF 기상 · 30분 단위"],
    ["notam", "FAA SWIM NOTAM · 실시간"],
    ["atfm-restriction", "ATFM GDP/slot · on-demand"],
    ["alert-decision", "이상 탐지 결과 · 실시간"],
    ["acdm-milestone", "A-CDM 16 milestone · P8"],
  ];
  topics.forEach((t, i) => {
    const y = 1.5 + i * 0.5;
    s.addText([
      { text: "• ", options: { color: C.amber, bold: true } },
      { text: t[0], options: { color: C.white, fontSize: 11, bold: true } },
    ], { x: 5.5, y, w: 4.0, h: 0.25, fontFace: FONT_T, margin: 0 });
    s.addText(t[1], {
      x: 5.7, y: y + 0.22, w: 3.8, h: 0.23, fontSize: 9, color: C.ice,
      fontFace: FONT_B, margin: 0
    });
  });

  addFooter(s, 7, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 8 · PyFlink + Redis
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 03 · 데이터 수집", "PyFlink + Redis — 실시간 처리");

  // 좌측: Apache Flink
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.0, w: 4.4, h: 3.9, fill: { color: C.white }, line: { color: C.ice, width: 1 }
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.0, w: 4.4, h: 0.45, fill: { color: C.skyBlue }, line: { color: C.skyBlue }
  });
  s.addText("⚡ Apache Flink (PyFlink)", {
    x: 0.65, y: 1.05, w: 4.1, h: 0.35, fontSize: 14, bold: true, color: C.white,
    fontFace: FONT_T, margin: 0
  });

  s.addText("왜 Flink? — 왜 Spark 가 아닌가?", {
    x: 0.7, y: 1.6, w: 4.1, h: 0.3, fontSize: 11, bold: true, color: C.navy,
    fontFace: FONT_T, margin: 0
  });
  const flinkPoints = [
    "True streaming — Spark 는 micro-batch 지만 Flink 는 이벤트 단위 실시간 처리",
    "Event-time + Watermark — 네트워크 지연으로 늦게 도착하는 ADS-B 이벤트도 올바른 시간 기준 집계",
    "5분 Tumbling Window 로 공항별 시간당 출발/도착 편수 집계 → XGBoost feature 주입",
    "CEP (Complex Event Processing) 룰 엔진으로 이상 패턴 감지",
  ];
  flinkPoints.forEach((p, i) => {
    const y = 1.95 + i * 0.65;
    s.addText("→ " + p, {
      x: 0.7, y, w: 4.1, h: 0.6, fontSize: 10, color: C.slate, fontFace: FONT_B, margin: 0
    });
  });

  // 우측: Redis
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 1.0, w: 4.4, h: 3.9, fill: { color: C.white }, line: { color: C.ice, width: 1 }
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 1.0, w: 4.4, h: 0.45, fill: { color: C.coral }, line: { color: C.coral }
  });
  s.addText("🔴 Redis — In-memory Store", {
    x: 5.25, y: 1.05, w: 4.1, h: 0.35, fontSize: 14, bold: true, color: C.white,
    fontFace: FONT_T, margin: 0
  });

  s.addText("왜 Redis? — 마이크로초 latency 필요", {
    x: 5.3, y: 1.6, w: 4.1, h: 0.3, fontSize: 11, bold: true, color: C.navy,
    fontFace: FONT_T, margin: 0
  });
  const redisPoints = [
    "관제사가 대시보드에서 실시간 항공기 위치를 보려면 p95 < 30ms 응답 필수",
    "DB 조회 대신 Redis Sorted Set 에 aircraft state 캐싱 — RAM 기반 μs 단위",
    "Debouncing (알람 억제) — TTL 60s 키로 같은 이상 반복 방지",
    "Feast Feature Store online layer — 지연 예측 feature 즉시 제공",
  ];
  redisPoints.forEach((p, i) => {
    const y = 1.95 + i * 0.65;
    s.addText("→ " + p, {
      x: 5.3, y, w: 4.1, h: 0.6, fontSize: 10, color: C.slate, fontFace: FONT_B, margin: 0
    });
  });

  addFooter(s, 8, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 9 · XGBoost 지연 예측
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 04 · ML 모델 · 지연 예측", "왜 XGBoost 인가?");

  // 좌측
  s.addText("📊 XGBoost (Extreme Gradient Boosting)", {
    x: 0.5, y: 1.0, w: 9.5, h: 0.4, fontSize: 16, bold: true, color: C.navy,
    fontFace: FONT_T, margin: 0
  });
  s.addText("캐글 대회·실무 Tabular 데이터의 사실상 표준 — 2014 Tianqi Chen 개발, 트리 기반 앙상블", {
    x: 0.5, y: 1.35, w: 9.5, h: 0.3, fontSize: 11, italic: true, color: C.mute,
    fontFace: FONT_B, margin: 0
  });

  // 왜 이걸 선택?
  const reasons = [
    ["정확도", "캐글 대회 우승 모델 대부분 · tabular 데이터에서 딥러닝 대비 동등 이상 성능", C.teal],
    ["속도", "병렬 학습 + 히스토그램 기반 split → 5.7M rows 4분 학습 (RTX 3070 없이도 CPU 로 가능)", C.skyBlue],
    ["해석성", "SHAP TreeExplainer 지원 → 「왜 이 항공편이 지연될 거라고 예측했는가」 feature 기여도 시각화", C.amber],
    ["robust", "결측값·이상치에 강함 · categorical encoding 자동 처리 · normalization 불필요", C.coral],
  ];
  reasons.forEach((r, i) => {
    const y = 1.8 + i * 0.7;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y, w: 1.4, h: 0.6, fill: { color: r[2] }, line: { color: r[2] }
    });
    s.addText(r[0], {
      x: 0.5, y, w: 1.4, h: 0.6, fontSize: 13, bold: true, color: C.white,
      fontFace: FONT_T, align: "center", valign: "middle", margin: 0
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 1.9, y, w: 7.6, h: 0.6, fill: { color: C.white }, line: { color: C.ice, width: 1 }
    });
    s.addText(r[1], {
      x: 2.0, y, w: 7.5, h: 0.6, fontSize: 10, color: C.slate, fontFace: FONT_B,
      valign: "middle", margin: 0
    });
  });

  // 하단 결과 박스
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.75, w: 9, h: 0.4, fill: { color: C.navy }, line: { color: C.navy }
  });
  s.addText([
    { text: "✈ 우리 프로젝트 실측 결과:  ", options: { color: C.amber, bold: true, fontSize: 11 } },
    { text: "Test RMSE 28.18분  ·  Test R² 0.4328  ·  분류 정확도 89.04%  ·  학습 시간 4분", options: { color: C.white, fontSize: 11 } }
  ], { x: 0.7, y: 4.78, w: 8.8, h: 0.35, fontFace: FONT_B, margin: 0 });

  addFooter(s, 9, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 10 · TimeSeriesSplit + Rotation features
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 04 · ML 모델 · 지연 예측", "P0+P1: 평가 정직화 + 운항 네트워크 Feature");

  // 좌측: TimeSeriesSplit
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.0, w: 4.4, h: 1.85, fill: { color: C.white }, line: { color: C.ice, width: 1 }
  });
  s.addText("P0: TimeSeriesSplit 전환", {
    x: 0.65, y: 1.1, w: 4.1, h: 0.3, fontSize: 13, bold: true, color: C.navy, fontFace: FONT_T, margin: 0
  });
  s.addText("기존 KFold(shuffle=True) 는 미래 데이터로 과거를 예측하는 temporal leakage 발생", {
    x: 0.65, y: 1.4, w: 4.1, h: 0.5, fontSize: 9, italic: true, color: C.mute, fontFace: FONT_B, margin: 0
  });
  s.addText("→ TimeSeriesSplit walk-forward validation 으로 교체", {
    x: 0.65, y: 1.9, w: 4.1, h: 0.25, fontSize: 10, bold: true, color: C.teal, fontFace: FONT_B, margin: 0
  });
  s.addText([
    { text: "결과:  ", options: { color: C.navy, bold: true } },
    { text: "CV 표준편차 ±0.30 → ±6.14", options: { color: C.slate } },
    { text: " (시간대별 변동성 정직 노출)", options: { color: C.mute, italic: true } },
  ], { x: 0.65, y: 2.2, w: 4.1, h: 0.5, fontSize: 9, fontFace: FONT_B, margin: 0 });

  // 우측: Rotation features
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 1.0, w: 4.4, h: 1.85, fill: { color: C.white }, line: { color: C.ice, width: 1 }
  });
  s.addText("P1: Rotation Features 5종 추가 🔥", {
    x: 5.25, y: 1.1, w: 4.1, h: 0.3, fontSize: 13, bold: true, color: C.navy, fontFace: FONT_T, margin: 0
  });
  s.addText("EUROCONTROL CODA: 지연의 45%는 reactionary (전편 지연의 파급)", {
    x: 5.25, y: 1.4, w: 4.1, h: 0.3, fontSize: 9, italic: true, color: C.mute, fontFace: FONT_B, margin: 0
  });
  s.addText("rotation_depth · prev_leg_arr_delay · turnaround_min · is_first_leg", {
    x: 5.25, y: 1.75, w: 4.1, h: 0.3, fontSize: 9, color: C.slate, fontFace: FONT_B, margin: 0
  });
  s.addText([
    { text: "결과:  ", options: { color: C.navy, bold: true } },
    { text: "Test R² 0.0996 → ", options: { color: C.slate } },
    { text: "0.4328 (+335%)", options: { color: C.teal, bold: true } },
  ], { x: 5.25, y: 2.25, w: 4.1, h: 0.45, fontSize: 10, fontFace: FONT_B, margin: 0 });

  // 하단: 성능 표
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 3.1, w: 9, h: 0.4, fill: { color: C.navy }, line: { color: C.navy }
  });
  s.addText("P0 → P1 성능 변화 (TimeSeriesSplit + Rotation features)", {
    x: 0.65, y: 3.15, w: 8.7, h: 0.3, fontSize: 12, bold: true, color: C.amber, fontFace: FONT_T, margin: 0
  });

  const rows = [
    ["지표", "P0 Baseline", "P1 최종", "변화"],
    ["Val RMSE (분)", "24.60", "22.61", "-8.1%"],
    ["Test RMSE (분)", "36.52", "28.18", "-22.8%"],
    ["Test R²", "0.0996", "0.4328", "+335% 🔥"],
    ["5-Fold CV std", "±6.14", "±1.51", "4배 안정"],
    ["Val-Test gap (분)", "12", "5.5", "절반"],
  ];
  rows.forEach((row, i) => {
    const y = 3.55 + i * 0.28;
    row.forEach((cell, j) => {
      const x = 0.5 + [0, 3, 5.5, 8][j];
      const w = [3, 2.5, 2.5, 1.5][j];
      s.addShape(pres.shapes.RECTANGLE, {
        x, y, w, h: 0.27,
        fill: { color: i === 0 ? C.skyBlue : (i % 2 === 0 ? C.white : C.ice) },
        line: { color: C.ice, width: 0.5 }
      });
      s.addText(cell, {
        x, y, w, h: 0.27, fontSize: 10,
        bold: i === 0 || j === 3,
        color: i === 0 ? C.white : (j === 3 ? C.teal : C.slate),
        fontFace: FONT_B, align: "center", valign: "middle", margin: 0
      });
    });
  });

  addFooter(s, 10, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 11 · Conformal Prediction
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 04 · ML 모델 · 지연 예측", "Conformal Prediction — 확률적 예측구간");

  s.addText("💡 왜 Conformal Prediction 인가?", {
    x: 0.5, y: 1.0, w: 9, h: 0.4, fontSize: 16, bold: true, color: C.navy, fontFace: FONT_T, margin: 0
  });
  s.addText("기존 예측: 「15분 지연될 겁니다」 → 정말 15분? 실제는 5분일 수도 40분일 수도", {
    x: 0.5, y: 1.4, w: 9, h: 0.3, fontSize: 11, italic: true, color: C.mute, fontFace: FONT_B, margin: 0
  });

  // 차이 비교 박스
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.85, w: 4.4, h: 1.5, fill: { color: C.ice }, line: { color: C.skyBlue, width: 1 }
  });
  s.addText("❌ 전통적 point estimate", {
    x: 0.65, y: 1.95, w: 4.1, h: 0.3, fontSize: 12, bold: true, color: C.coral, fontFace: FONT_T, margin: 0
  });
  s.addText("\"예상 지연 15분\"\n\n• 얼마나 확신할 수 있나? 모름\n• 위험 감수 판단 불가능\n• Heuristic confidence (high/low) 는 근거 없음", {
    x: 0.65, y: 2.3, w: 4.1, h: 1.0, fontSize: 10, color: C.slate, fontFace: FONT_B, margin: 0
  });

  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 1.85, w: 4.4, h: 1.5, fill: { color: C.teal, transparency: 85 }, line: { color: C.teal, width: 1 }
  });
  s.addText("✅ Conformal prediction interval", {
    x: 5.25, y: 1.95, w: 4.1, h: 0.3, fontSize: 12, bold: true, color: C.teal, fontFace: FONT_T, margin: 0
  });
  s.addText("\"90% 확률로 6~41분 지연\"\n\n• 분포 가정 없이 수학적으로 보장\n• Empirical coverage 실측 90.00%\n• 관제사가 정량적 위험 판단 가능", {
    x: 5.25, y: 2.3, w: 4.1, h: 1.0, fontSize: 10, color: C.slate, fontFace: FONT_B, margin: 0
  });

  // 구현 방식
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 3.55, w: 9, h: 1.4, fill: { color: C.white }, line: { color: C.ice, width: 1 }
  });
  s.addText("구현 방식 — MAPIE 1.3 (Model Agnostic Prediction Intervals Estimator)", {
    x: 0.65, y: 3.6, w: 8.7, h: 0.3, fontSize: 12, bold: true, color: C.navy, fontFace: FONT_T, margin: 0
  });
  s.addText([
    { text: "1. Split Conformal:  ", options: { bold: true, color: C.skyBlue } },
    { text: "Train → 별도 calibration set 에서 절대 residual 계산 → 양측 대칭 interval", options: { color: C.slate } },
    { text: "\n2. CQR (P4+):  ", options: { bold: true, color: C.teal, breakLine: false } },
    { text: "Conformalized Quantile Regression → low/high quantile 모델 2개 + conformity score → 비대칭 interval (기상 왜곡 분포 반영)", options: { color: C.slate } },
    { text: "\n3. 어디에 쓰이나:  ", options: { bold: true, color: C.amber, breakLine: false } },
    { text: "의료 진단, 금융 VaR, 자율주행 안전 margin — 이론 보장 유효 예측구간이 필요한 고위험 도메인", options: { color: C.slate } },
  ], { x: 0.65, y: 3.95, w: 8.7, h: 0.95, fontSize: 10, fontFace: FONT_B, margin: 0 });

  addFooter(s, 11, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 12 · Isolation Forest 이상 탐지
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 05 · ML 모델 · 이상 탐지", "Isolation Forest 원리");

  // 좌측 개념
  s.addText("🌲 Isolation Forest (2008, Liu et al.)", {
    x: 0.5, y: 1.0, w: 9, h: 0.4, fontSize: 16, bold: true, color: C.navy, fontFace: FONT_T, margin: 0
  });
  s.addText("「이상치는 소수이고 다른 데이터와 거리가 멀다」— 트리에서 빨리 isolation 됨", {
    x: 0.5, y: 1.4, w: 9, h: 0.3, fontSize: 11, italic: true, color: C.mute, fontFace: FONT_B, margin: 0
  });

  // 좌측: 원리 설명
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.85, w: 4.4, h: 3.1, fill: { color: C.white }, line: { color: C.ice, width: 1 }
  });
  s.addText("핵심 아이디어", {
    x: 0.65, y: 1.95, w: 4.1, h: 0.3, fontSize: 13, bold: true, color: C.navy, fontFace: FONT_T, margin: 0
  });
  const principles = [
    "랜덤 트리들을 만들어서 data 를 재귀적으로 분할",
    "정상 data 는 깊은 트리에서 분리됨 (path long)",
    "이상 data 는 얕은 트리에서 분리됨 (path short)",
    "여러 트리의 평균 path length 로 anomaly score 계산",
    "비지도 학습 — label 없어도 동작 (항공 사고 data 는 희귀)",
  ];
  principles.forEach((p, i) => {
    const y = 2.3 + i * 0.48;
    s.addText("• " + p, {
      x: 0.7, y, w: 4.1, h: 0.45, fontSize: 10, color: C.slate, fontFace: FONT_B, margin: 0
    });
  });

  // 우측: 왜 이걸 선택
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 1.85, w: 4.4, h: 3.1, fill: { color: C.white }, line: { color: C.ice, width: 1 }
  });
  s.addText("왜 Autoencoder / One-class SVM 이 아닌가?", {
    x: 5.25, y: 1.95, w: 4.1, h: 0.3, fontSize: 13, bold: true, color: C.navy, fontFace: FONT_T, margin: 0
  });
  const vs = [
    ["vs Autoencoder", "딥러닝은 GPU 필요 + 학습 안정성 떨어짐. IF 는 CPU 에서 분 단위 학습"],
    ["vs One-class SVM", "SVM 은 O(n²~n³) 로 대용량에 느림. IF 는 O(n log n)"],
    ["vs 통계적 규칙", "\"고도 > 40,000ft\" 같은 단일 threshold 는 cruise 정상을 오탐"],
    ["vs LSTM Autoencoder", "시계열 학습 복잡. 현재 snapshot feature 로도 충분한 성능"],
  ];
  vs.forEach((v, i) => {
    const y = 2.3 + i * 0.62;
    s.addText(v[0], {
      x: 5.25, y, w: 4.1, h: 0.22, fontSize: 10, bold: true, color: C.skyBlue, fontFace: FONT_T, margin: 0
    });
    s.addText(v[1], {
      x: 5.25, y: y + 0.22, w: 4.1, h: 0.35, fontSize: 9, color: C.slate, fontFace: FONT_B, margin: 0
    });
  });

  addFooter(s, 12, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 13 · Per-phase IF ×7
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 05 · ML 모델 · 이상 탐지", "P5+: Phase-aware Per-phase IF ×7");

  s.addText("💡 비행 단계별로 정상이 완전히 다르다", {
    x: 0.5, y: 1.0, w: 9, h: 0.35, fontSize: 16, bold: true, color: C.navy, fontFace: FONT_T, margin: 0
  });
  s.addText("CRUISE 에서 30,000ft 는 정상 · LANDING 에서 30,000ft 는 비정상. 단일 모델로는 구분 불가.", {
    x: 0.5, y: 1.35, w: 9, h: 0.3, fontSize: 11, italic: true, color: C.mute, fontFace: FONT_B, margin: 0
  });

  // 7 phase 카드
  const phases = [
    ["TAXI",      "0.02", "활주로 이동 — 저고도·저속. 이상: 속도 급증"],
    ["TAKEOFF",   "0.03", "이륙 — 고속 가속. 이상: 고도 급락"],
    ["CLIMB",     "0.04", "상승 — 일정 VS. 이상: 급격한 방향 변경"],
    ["CRUISE",    "0.05", "순항 — 대부분 시간. 이상: 고도 급변·emergency squawk"],
    ["DESCENT",   "0.04", "하강 — -500~-1500 fpm. 이상: 너무 빠른 하강"],
    ["APPROACH",  "0.06", "접근 — 공항 반경 30NM. 안전 요주의 (사고 빈발)"],
    ["LANDING",   "0.06", "착륙 — 최저 고도. 이상: 복행 후 동일 시나리오 반복"],
  ];
  phases.forEach((p, i) => {
    const col = i % 4, row = Math.floor(i / 4);
    const x = 0.4 + col * 2.35;
    const y = 1.85 + row * 1.35;

    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 2.25, h: 1.25, fill: { color: C.white }, line: { color: C.ice, width: 1 }
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 2.25, h: 0.35, fill: { color: C.skyBlue }, line: { color: C.skyBlue }
    });
    s.addText(p[0], {
      x, y: y + 0.04, w: 2.25, h: 0.27, fontSize: 12, bold: true, color: C.white,
      fontFace: FONT_T, align: "center", margin: 0
    });
    s.addText("contam " + p[1], {
      x, y: y + 0.4, w: 2.25, h: 0.25, fontSize: 10, color: C.teal, bold: true,
      fontFace: FONT_B, align: "center", margin: 0
    });
    s.addText(p[2], {
      x: x + 0.1, y: y + 0.62, w: 2.1, h: 0.6, fontSize: 8, color: C.slate,
      fontFace: FONT_B, margin: 0
    });
  });

  // 마지막 슬롯에 요약
  const x = 0.4 + 3 * 2.35, y = 1.85 + 1.35;
  s.addShape(pres.shapes.RECTANGLE, {
    x, y, w: 2.25, h: 1.25, fill: { color: C.navy }, line: { color: C.navy }
  });
  s.addText("✓ 결과", {
    x: x + 0.15, y: y + 0.1, w: 2.0, h: 0.3, fontSize: 12, bold: true, color: C.amber,
    fontFace: FONT_T, margin: 0
  });
  s.addText("ML phase classifier 와 결합\nheuristic 대비 90.3% agreement\nalert fatigue 67% 감소", {
    x: x + 0.15, y: y + 0.4, w: 2.0, h: 0.85, fontSize: 9, color: C.white,
    fontFace: FONT_B, margin: 0
  });

  addFooter(s, 13, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 14 · Active Learning
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 05 · ML 모델 · 이상 탐지", "Active Learning 자동 재학습 Loop");

  s.addText("🔄 분석가 피드백 → 모델 재학습 자동화", {
    x: 0.5, y: 1.0, w: 9, h: 0.35, fontSize: 16, bold: true, color: C.navy, fontFace: FONT_T, margin: 0
  });

  // 5 단계 flow
  const stages = [
    ["① 이상 탐지", "API가 AnomalyEvent 생성 · alert_id 할당", C.skyBlue],
    ["② 분석가 라벨링", "dashboard에서 TP/FP/Uncertain 클릭", C.teal],
    ["③ 자동 분석", "Airflow daily 02:00 · FP rate 계산", C.amber],
    ["④ contamination tune", "FP > 35% → 낮춤 · FP < 10% → 높임", C.coral],
    ["⑤ IF 재학습 + 핫리로드", ".reload_signal → ModelStore mtime watch", C.navy],
  ];
  stages.forEach((st, i) => {
    const y = 1.5 + i * 0.7;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y, w: 2.3, h: 0.6, fill: { color: st[2] }, line: { color: st[2] }
    });
    s.addText(st[0], {
      x: 0.5, y, w: 2.3, h: 0.6, fontSize: 12, bold: true, color: C.white,
      fontFace: FONT_T, align: "center", valign: "middle", margin: 0
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 2.9, y, w: 6.6, h: 0.6, fill: { color: C.white }, line: { color: C.ice, width: 1 }
    });
    s.addText(st[1], {
      x: 3.05, y, w: 6.4, h: 0.6, fontSize: 10, color: C.slate, fontFace: FONT_B,
      valign: "middle", margin: 0
    });
    // 화살표 (마지막 제외)
    if (i < stages.length - 1) {
      s.addText("↓", {
        x: 1.6, y: y + 0.6, w: 0.2, h: 0.1, fontSize: 12, color: C.mute, fontFace: FONT_T,
        align: "center", margin: 0
      });
    }
  });

  // 하단 추가: P7-C Bandit v2
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 5.0, w: 9, h: 0.3, fill: { color: C.teal }, line: { color: C.teal }
  });
  s.addText([
    { text: "P7-C Bandit v2:  ", options: { color: C.white, bold: true, fontSize: 10 } },
    { text: "Thompson sampling on Beta(1+TP, 1+FP) + (type, phase) 다양성 라운드로빈 → homogeneous queue 해소", options: { color: C.ice, fontSize: 10 } },
  ], { x: 0.65, y: 5.03, w: 8.7, h: 0.25, fontFace: FONT_B, margin: 0 });

  addFooter(s, 14, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 15 · LLM 선택 이유
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 06 · LLM · AI 어시스턴트", "왜 Qwen2.5-7B 인가?");

  s.addText("🤖 Qwen2.5-7B-Instruct (Alibaba, 2024)", {
    x: 0.5, y: 1.0, w: 9, h: 0.4, fontSize: 16, bold: true, color: C.navy, fontFace: FONT_T, margin: 0
  });
  s.addText("7B 파라미터 instruction-tuned LLM · Apache 2.0 오픈소스 · 18조 토큰 학습", {
    x: 0.5, y: 1.4, w: 9, h: 0.3, fontSize: 11, italic: true, color: C.mute, fontFace: FONT_B, margin: 0
  });

  // 2x2 비교 카드
  const compare = [
    ["vs Llama-3-8B",     "동등 성능, 중국어·한국어 품질 우위 (ATC 대화 학습에 유리)", C.skyBlue],
    ["vs Gemini/GPT-4",    "On-premise 가능 (항공 안전 데이터 외부 전송 금지)", C.teal],
    ["vs Qwen 72B",        "7B 면 RTX 3070 8GB (AWQ 4-bit) 로 40 tok/s 가능", C.amber],
    ["vs Mistral-7B",       "한국어 평가 benchmark (KMMLU, KoBEST) 점수 우위", C.coral],
  ];
  compare.forEach((c, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.4 + col * 4.75;
    const y = 1.95 + row * 1.1;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 4.6, h: 1.0, fill: { color: C.white }, line: { color: C.ice, width: 1 }
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 4.6, h: 0.35, fill: { color: c[2] }, line: { color: c[2] }
    });
    s.addText(c[0], {
      x: x + 0.15, y: y + 0.04, w: 4.3, h: 0.27, fontSize: 12, bold: true, color: C.white,
      fontFace: FONT_T, margin: 0
    });
    s.addText(c[1], {
      x: x + 0.15, y: y + 0.4, w: 4.3, h: 0.6, fontSize: 10, color: C.slate, fontFace: FONT_B, margin: 0
    });
  });

  // 하단 결과
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.3, w: 9, h: 0.8, fill: { color: C.navy }, line: { color: C.navy }
  });
  s.addText("✈ 실제 파인튜닝 결과", {
    x: 0.65, y: 4.38, w: 8.7, h: 0.25, fontSize: 11, bold: true, color: C.amber, fontFace: FONT_T, margin: 0
  });
  s.addText([
    { text: "QLoRA Train Loss 0.1053  ·  ", options: { color: C.white, fontSize: 10 } },
    { text: "Eval Token Accuracy 97.88%", options: { color: C.teal, fontSize: 10, bold: true } },
    { text: "  ·  DPO Rewards Accuracy ", options: { color: C.white, fontSize: 10 } },
    { text: "100%", options: { color: C.teal, fontSize: 10, bold: true } },
    { text: "  ·  학습 데이터 13,969건 + 한국 SFT 3,500 시드", options: { color: C.white, fontSize: 10 } },
  ], { x: 0.65, y: 4.65, w: 8.7, h: 0.4, fontFace: FONT_B, margin: 0 });

  addFooter(s, 15, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 16 · QLoRA
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 06 · LLM · AI 어시스턴트", "QLoRA — 4-bit Quantized LoRA Fine-tuning");

  // 개념 박스
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.0, w: 9, h: 0.6, fill: { color: C.navy }, line: { color: C.navy }
  });
  s.addText("💡 7B 모델을 RTX 3070 (8GB VRAM) 에 어떻게 학습할 것인가?", {
    x: 0.65, y: 1.08, w: 8.7, h: 0.25, fontSize: 13, bold: true, color: C.amber, fontFace: FONT_T, margin: 0
  });
  s.addText("Full Fine-tuning 은 ~60GB VRAM 필요 · QLoRA 로 6GB 까지 축소 → 홈 GPU 에서 학습 가능", {
    x: 0.65, y: 1.32, w: 8.7, h: 0.25, fontSize: 10, color: C.white, fontFace: FONT_B, margin: 0
  });

  // 3단계 메커니즘
  const steps = [
    ["① 4-bit Quantization", "Base model 가중치를 FP16 → NF4 (4-bit NormalFloat) 로 압축. 16배 메모리 절감", C.skyBlue],
    ["② LoRA Adapter 추가", "원본 가중치는 frozen · Low-Rank Adapter 행렬만 학습 (rank=64). 학습 파라미터 0.1% 수준", C.teal],
    ["③ Gradient Checkpointing", "Forward pass 결과를 저장 대신 재계산 → 메모리 시간 tradeoff · 대용량 배치 가능", C.amber],
  ];
  steps.forEach((st, i) => {
    const y = 1.9 + i * 0.85;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y, w: 2.5, h: 0.75, fill: { color: st[2] }, line: { color: st[2] }
    });
    s.addText(st[0], {
      x: 0.5, y, w: 2.5, h: 0.75, fontSize: 12, bold: true, color: C.white,
      fontFace: FONT_T, align: "center", valign: "middle", margin: 0
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 3.1, y, w: 6.4, h: 0.75, fill: { color: C.white }, line: { color: C.ice, width: 1 }
    });
    s.addText(st[1], {
      x: 3.2, y, w: 6.2, h: 0.75, fontSize: 10, color: C.slate, fontFace: FONT_B,
      valign: "middle", margin: 0
    });
  });

  // 하단 통계
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.75, w: 9, h: 0.4, fill: { color: C.ice }, line: { color: C.skyBlue, width: 1 }
  });
  s.addText([
    { text: "🖥 학습 spec:  ", options: { color: C.navy, bold: true, fontSize: 10 } },
    { text: "RTX 3070 (8GB) · 학습시간 9시간 · batch 4 · 총 데이터 13,969건 · TRL SFTTrainer", options: { color: C.slate, fontSize: 10 } },
  ], { x: 0.65, y: 4.78, w: 8.7, h: 0.34, fontFace: FONT_B, margin: 0 });

  addFooter(s, 16, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 17 · DPO
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 06 · LLM · AI 어시스턴트", "DPO — 선호도 학습 (Human Alignment)");

  s.addText("🎯 \"학습된 모델이 생성하는 답변 중 어떤 게 더 좋은가?\"", {
    x: 0.5, y: 1.0, w: 9, h: 0.4, fontSize: 15, bold: true, color: C.navy, fontFace: FONT_T, margin: 0
  });
  s.addText("SFT 만으로는 \"정답\" 은 학습해도 \"선호되는 답변 스타일\" 은 학습 못 함", {
    x: 0.5, y: 1.4, w: 9, h: 0.3, fontSize: 11, italic: true, color: C.mute, fontFace: FONT_B, margin: 0
  });

  // DPO vs RLHF
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.85, w: 4.4, h: 2, fill: { color: C.white }, line: { color: C.ice, width: 1 }
  });
  s.addText("DPO (Direct Preference Optimization)", {
    x: 0.65, y: 1.95, w: 4.1, h: 0.3, fontSize: 12, bold: true, color: C.teal, fontFace: FONT_T, margin: 0
  });
  s.addText("• chosen / rejected 페어만으로 학습\n• Reward Model 불필요 → 간단 + 안정\n• RLHF 3단계 축소\n• 2023 Stanford, NeurIPS Best Paper", {
    x: 0.65, y: 2.3, w: 4.1, h: 1.5, fontSize: 10, color: C.slate, fontFace: FONT_B, margin: 0
  });

  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 1.85, w: 4.4, h: 2, fill: { color: C.ice }, line: { color: C.ice, width: 1 }
  });
  s.addText("예시 (항공 도메인)", {
    x: 5.25, y: 1.95, w: 4.1, h: 0.3, fontSize: 12, bold: true, color: C.navy, fontFace: FONT_T, margin: 0
  });
  s.addText([
    { text: "질문: ", options: { bold: true, color: C.navy } },
    { text: "\"윈드시어 감지 시 대응은?\"\n", options: { color: C.slate } },
    { text: "✅ chosen: ", options: { bold: true, color: C.teal, breakLine: false } },
    { text: "활주로 진입 대기, ATC 통보, 승객 안내. 필요 시 공항 변경 고려.\n", options: { color: C.slate } },
    { text: "❌ rejected: ", options: { bold: true, color: C.coral, breakLine: false } },
    { text: "Windshear detected. Follow the procedure.", options: { color: C.mute } },
  ], { x: 5.25, y: 2.3, w: 4.1, h: 1.5, fontSize: 9, fontFace: FONT_B, margin: 0 });

  // 사용처
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.0, w: 9, h: 1.15, fill: { color: C.navy }, line: { color: C.navy }
  });
  s.addText("🌐 DPO 가 주로 쓰이는 곳", {
    x: 0.65, y: 4.08, w: 8.7, h: 0.3, fontSize: 12, bold: true, color: C.amber, fontFace: FONT_T, margin: 0
  });
  s.addText([
    { text: "• ChatGPT / Claude  ", options: { color: C.white, fontSize: 10 } },
    { text: "(OpenAI, Anthropic 이 alignment 에 DPO 계열 사용)\n", options: { color: C.ice, fontSize: 10 } },
    { text: "• 의료 AI  ", options: { color: C.white, fontSize: 10, breakLine: false } },
    { text: "(환자 친화적 언어 선호)\n", options: { color: C.ice, fontSize: 10 } },
    { text: "• 법률 AI  ", options: { color: C.white, fontSize: 10, breakLine: false } },
    { text: "(한국 법률 용어 정확도 우선)\n", options: { color: C.ice, fontSize: 10 } },
    { text: "• 우리 프로젝트  ", options: { color: C.white, fontSize: 10, breakLine: false } },
    { text: "— 영어 잔존·중국어 코드스위칭·공손어 누락을 rejected 로 학습", options: { color: C.ice, fontSize: 10 } },
  ], { x: 0.65, y: 4.4, w: 8.7, h: 0.7, fontFace: FONT_B, margin: 0 });

  addFooter(s, 17, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 18 · RAG + ChromaDB
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 06 · LLM · AI 어시스턴트", "RAG — Retrieval-Augmented Generation");

  s.addText("💡 LLM 이 모르는 최신 규정·NOTAM 어떻게 답하나?", {
    x: 0.5, y: 1.0, w: 9, h: 0.4, fontSize: 16, bold: true, color: C.navy, fontFace: FONT_T, margin: 0
  });
  s.addText("Fine-tuning 만으로는 최신 NOTAM, 공항별 SOP 커버 불가 → RAG 로 외부 지식 주입", {
    x: 0.5, y: 1.4, w: 9, h: 0.3, fontSize: 11, italic: true, color: C.mute, fontFace: FONT_B, margin: 0
  });

  // RAG 파이프라인
  const stages = [
    ["질문", "「RKSI 활주로 15L 폐쇄 시 대응?」", C.skyBlue],
    ["Embed", "BAAI/bge-m3 로 쿼리 벡터화 (1024차원)", C.teal],
    ["Retrieve", "ChromaDB 161 chunks에서 top-k=4 검색", C.amber],
    ["Generate", "Qwen2.5 + 검색 컨텍스트로 답변 생성", C.coral],
  ];
  stages.forEach((st, i) => {
    const x = 0.5 + i * 2.35;
    const y = 1.9;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 2.15, h: 1.2, fill: { color: st[2] }, line: { color: st[2] }
    });
    s.addText(st[0], {
      x, y: y + 0.1, w: 2.15, h: 0.3, fontSize: 13, bold: true, color: C.white,
      fontFace: FONT_T, align: "center", margin: 0
    });
    s.addText(st[1], {
      x: x + 0.1, y: y + 0.45, w: 1.95, h: 0.65, fontSize: 9, color: C.white,
      fontFace: FONT_B, align: "center", margin: 0
    });
    if (i < 3) {
      s.addText("→", {
        x: x + 2.15, y: y + 0.5, w: 0.2, h: 0.3, fontSize: 16, color: C.mute,
        fontFace: FONT_T, align: "center", bold: true, margin: 0
      });
    }
  });

  // ChromaDB 설명
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 3.4, w: 9, h: 1.75, fill: { color: C.white }, line: { color: C.ice, width: 1 }
  });
  s.addText("📚 ChromaDB — 왜 이 벡터 DB?", {
    x: 0.65, y: 3.5, w: 8.7, h: 0.3, fontSize: 13, bold: true, color: C.navy, fontFace: FONT_T, margin: 0
  });
  s.addText([
    { text: "• 오픈소스·파이썬 우선  ", options: { color: C.navy, bold: true } },
    { text: "(vs Pinecone 유료, Weaviate 복잡)\n", options: { color: C.slate } },
    { text: "• 임베디드 모드  ", options: { color: C.navy, bold: true, breakLine: false } },
    { text: "(SQLite + Parquet) — 별도 서버 불필요, persist 지원\n", options: { color: C.slate } },
    { text: "• BAAI/bge-m3 임베딩  ", options: { color: C.navy, bold: true, breakLine: false } },
    { text: "— 다국어 (한국어·영어·중국어 동시), MTEB benchmark 최상위\n", options: { color: C.slate } },
    { text: "• 코퍼스 구성  ", options: { color: C.navy, bold: true, breakLine: false } },
    { text: "— FAA AIM (26), ICAO Annex (20), SOP (25), runbook (18), RKSI specific (15), airport_ops (21), notam samples (13), faa_ac (12), atc/기타 (11) = ", options: { color: C.slate } },
    { text: "총 161 chunks", options: { color: C.teal, bold: true } },
  ], { x: 0.65, y: 3.85, w: 8.7, h: 1.25, fontSize: 10, fontFace: FONT_B, margin: 0 });

  addFooter(s, 18, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 19 · FastAPI + vLLM
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 07 · 서빙 · 대시보드", "FastAPI + vLLM");

  // 좌: FastAPI
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.0, w: 4.4, h: 3.9, fill: { color: C.white }, line: { color: C.ice, width: 1 }
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.0, w: 4.4, h: 0.5, fill: { color: C.teal }, line: { color: C.teal }
  });
  s.addText("⚡ FastAPI 2.1.1 (15 endpoints)", {
    x: 0.65, y: 1.08, w: 4.1, h: 0.35, fontSize: 13, bold: true, color: C.white, fontFace: FONT_T, margin: 0
  });

  s.addText("왜 FastAPI 인가?", {
    x: 0.65, y: 1.6, w: 4.1, h: 0.3, fontSize: 12, bold: true, color: C.navy, fontFace: FONT_T, margin: 0
  });
  const fa = [
    "Pydantic v2 — request/response schema 자동 검증. Typo 즉시 거부",
    "Swagger UI 자동 — /docs 에서 interactive 문서화 (Flask 는 별도 library 필요)",
    "Async / await 네이티브 — vLLM · Redis · DB 동시 호출 병목 없음",
    "WebSocket first-class — dashboard 실시간 push 에 필수",
    "ADR-001 Phase 1 후 router 6개 분리 (api.py 1120→107라인)",
  ];
  fa.forEach((t, i) => {
    const y = 1.95 + i * 0.55;
    s.addText("• " + t, {
      x: 0.7, y, w: 4.1, h: 0.5, fontSize: 9, color: C.slate, fontFace: FONT_B, margin: 0
    });
  });

  // 우: vLLM
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 1.0, w: 4.4, h: 3.9, fill: { color: C.white }, line: { color: C.ice, width: 1 }
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 1.0, w: 4.4, h: 0.5, fill: { color: C.amber }, line: { color: C.amber }
  });
  s.addText("🚀 vLLM — 고성능 LLM 서빙", {
    x: 5.25, y: 1.08, w: 4.1, h: 0.35, fontSize: 13, bold: true, color: C.white, fontFace: FONT_T, margin: 0
  });

  s.addText("왜 vLLM 인가? (vs HuggingFace Transformers)", {
    x: 5.25, y: 1.6, w: 4.1, h: 0.3, fontSize: 12, bold: true, color: C.navy, fontFace: FONT_T, margin: 0
  });
  const vl = [
    "PagedAttention — GPU 메모리를 OS 페이징처럼 관리. 메모리 fragmentation 해소",
    "Continuous batching — 요청들이 각자 다른 길이여도 GPU 유휴 없이 처리",
    "AWQ 4-bit — 정확도 유지하며 모델 크기 4배 압축",
    "OpenAI 호환 API — 기존 code 수정 없이 drop-in replacement",
    "RTX 3070 에서 40 tok/s (Transformers 13 tok/s 대비 3배)",
  ];
  vl.forEach((t, i) => {
    const y = 1.95 + i * 0.55;
    s.addText("• " + t, {
      x: 5.3, y, w: 4.1, h: 0.5, fontSize: 9, color: C.slate, fontFace: FONT_B, margin: 0
    });
  });

  addFooter(s, 19, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 20 · Next.js Dashboard
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 07 · 서빙 · 대시보드", "Next.js 16 관제 대시보드 (7 페이지)");

  const pages = [
    ["대시보드 개요", "/", "KPI 카드 4종 + 최근 알림 + 항공기 요약"],
    ["실시간 지도", "/map", "Leaflet 라이브맵 (WebSocket + SWR fallback)"],
    ["이상 탐지", "/anomaly", "실시간 알림 피드 + 심각도 필터 + AI 분석 버튼"],
    ["NOTAM 실시간", "/notam", "SWIM 실 데이터 + 4 severity 필터 + 공항별 분포"],
    ["지연 예측", "/predict", "항공사/공항 폼 + Conformal interval 표시"],
    ["혼잡도 맵", "/heatmap", "MapLibre GL H3 R5 히트맵 (5초 갱신)"],
    ["AI 어시스턴트", "/chat", "RAG 채팅 + 시나리오 3종 + 승객 안내문"],
  ];
  pages.forEach((p, i) => {
    const y = 1.0 + i * 0.58;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y, w: 1.8, h: 0.5, fill: { color: C.skyBlue }, line: { color: C.skyBlue }
    });
    s.addText(p[0], {
      x: 0.5, y, w: 1.8, h: 0.5, fontSize: 11, bold: true, color: C.white,
      fontFace: FONT_T, align: "center", valign: "middle", margin: 0
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 2.4, y, w: 1.3, h: 0.5, fill: { color: C.navy }, line: { color: C.navy }
    });
    s.addText(p[1], {
      x: 2.4, y, w: 1.3, h: 0.5, fontSize: 10, color: C.amber, fontFace: "Consolas",
      align: "center", valign: "middle", margin: 0
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 3.8, y, w: 5.7, h: 0.5, fill: { color: C.white }, line: { color: C.ice, width: 1 }
    });
    s.addText(p[2], {
      x: 3.95, y, w: 5.5, h: 0.5, fontSize: 10, color: C.slate, fontFace: FONT_B,
      valign: "middle", margin: 0
    });
  });

  addFooter(s, 20, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 21 · MLOps Pipeline
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 08 · MLOps & Engineering", "MLOps 전체 파이프라인");

  const stack = [
    ["실험 관리", "MLflow", "학습 run 기록 · 하이퍼파라미터 · metrics · artifact 관리", C.skyBlue],
    ["워크플로", "Airflow", "일 1회 재학습 DAG · Active Learning retrain (02:00 UTC)", C.teal],
    ["드리프트", "EvidentlyAI", "Population Stability Index · 입력 분포 변화 자동 감지", C.amber],
    ["Feature Store", "Feast", "Offline parquet + Online Redis db=1 · training-serving skew 방지", C.coral],
    ["Data Lake", "Apache Iceberg", "Bronze/Silver/Gold 10 테이블 · snapshot · time-travel", C.navy],
    ["Data Lineage", "OpenLineage + Marquez", "dataset ↔ model ↔ deployment 추적", C.skyBlue],
    ["Schema Registry", "Confluent Avro", "5 topics (flight/weather/notam/atfm/alert) · BACKWARD compat", C.teal],
  ];
  stack.forEach((t, i) => {
    const y = 1.0 + i * 0.58;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y, w: 1.6, h: 0.5, fill: { color: t[3] }, line: { color: t[3] }
    });
    s.addText(t[0], {
      x: 0.5, y, w: 1.6, h: 0.5, fontSize: 10, bold: true, color: C.white,
      fontFace: FONT_T, align: "center", valign: "middle", margin: 0
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 2.2, y, w: 2.0, h: 0.5, fill: { color: C.white }, line: { color: C.ice, width: 1 }
    });
    s.addText(t[1], {
      x: 2.3, y, w: 1.9, h: 0.5, fontSize: 11, bold: true, color: C.navy,
      fontFace: FONT_T, valign: "middle", margin: 0
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 4.3, y, w: 5.2, h: 0.5, fill: { color: C.white }, line: { color: C.ice, width: 1 }
    });
    s.addText(t[2], {
      x: 4.4, y, w: 5.1, h: 0.5, fontSize: 9, color: C.slate, fontFace: FONT_B,
      valign: "middle", margin: 0
    });
  });

  addFooter(s, 21, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 22 · Observability
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 08 · MLOps & Engineering", "Observability 스택");

  s.addText("🔍 \"배포한 서비스가 실제로 건강한가?\" 를 측정 + 경보", {
    x: 0.5, y: 1.0, w: 9, h: 0.4, fontSize: 14, bold: true, color: C.navy, fontFace: FONT_T, margin: 0
  });

  const tools = [
    ["Jaeger", "분산 Trace", "요청 하나의 전 구간 (FastAPI → XGBoost → Redis) 추적 · p99 병목 시각화", C.teal],
    ["Prometheus", "시계열 메트릭", "서비스별 QPS · latency · error rate 수집 · PromQL 쿼리", C.skyBlue],
    ["Grafana", "대시보드 + 경보", "9-panel SLO 대시보드 + 3 alert rules (ErrorRate/Latency/Drift)", C.amber],
    ["OpenTelemetry", "계측 표준", "코드에서 OTLP gRPC 로 방출 · vendor-neutral (Datadog, New Relic 호환)", C.coral],
    ["Marquez", "OpenLineage UI", "모델 학습 run ↔ 입력 dataset ↔ 출력 table 연결 그래프", C.navy],
  ];
  tools.forEach((t, i) => {
    const y = 1.55 + i * 0.7;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y, w: 1.6, h: 0.62, fill: { color: t[3] }, line: { color: t[3] }
    });
    s.addText(t[0], {
      x: 0.5, y: y + 0.06, w: 1.6, h: 0.24, fontSize: 12, bold: true, color: C.white,
      fontFace: FONT_T, align: "center", margin: 0
    });
    s.addText(t[1], {
      x: 0.5, y: y + 0.32, w: 1.6, h: 0.23, fontSize: 8, color: C.white,
      fontFace: FONT_B, align: "center", margin: 0
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 2.2, y, w: 7.3, h: 0.62, fill: { color: C.white }, line: { color: C.ice, width: 1 }
    });
    s.addText(t[2], {
      x: 2.35, y, w: 7.1, h: 0.62, fontSize: 10, color: C.slate, fontFace: FONT_B,
      valign: "middle", margin: 0
    });
  });

  addFooter(s, 22, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 23 · 성능 지표 요약
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 09 · 성능 지표", "XGBoost 지연 예측 + IF 이상 탐지");

  // 좌: Stat cards
  const stats = [
    ["22.61", "Val RMSE\n(분)", C.skyBlue, "-8.1% vs P0"],
    ["0.4328", "Test R²\n", C.teal, "+335% vs P0"],
    ["89.04%", "분류 정확도\n(delay)", C.amber, "+4.88%p"],
    ["90.00%", "Conformal\ncoverage", C.coral, "목표 달성"],
  ];
  stats.forEach((st, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.4 + col * 2.3;
    const y = 1.0 + row * 1.35;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 2.2, h: 1.22, fill: { color: st[2] }, line: { color: st[2] }
    });
    s.addText(st[0], {
      x, y: y + 0.12, w: 2.2, h: 0.5, fontSize: 26, bold: true, color: C.white,
      fontFace: FONT_T, align: "center", valign: "middle", margin: 0
    });
    s.addText(st[1], {
      x, y: y + 0.62, w: 2.2, h: 0.35, fontSize: 9, color: C.white,
      fontFace: FONT_B, align: "center", margin: 0
    });
    s.addText(st[3], {
      x, y: y + 0.95, w: 2.2, h: 0.22, fontSize: 8, italic: true, color: C.ice,
      fontFace: FONT_B, align: "center", margin: 0
    });
  });

  // 우: LLM 지표
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 1.0, w: 4.4, h: 3.9, fill: { color: C.navy }, line: { color: C.navy }
  });
  s.addText("🤖 LLM + RAG 지표", {
    x: 5.25, y: 1.1, w: 4.1, h: 0.4, fontSize: 14, bold: true, color: C.amber,
    fontFace: FONT_T, margin: 0
  });

  const llmStats = [
    ["Train Loss (QLoRA)", "0.1053"],
    ["Eval Token Accuracy", "97.88%"],
    ["DPO Rewards Accuracy", "100%"],
    ["ROUGE-L (평가)", "0.169"],
    ["BLEU-1 (평가)", "0.121"],
    ["RAG chunks", "161 (6→161, +2583%)"],
    ["Korean SFT/DPO", "3,000 + 500 pairs"],
  ];
  llmStats.forEach((st, i) => {
    const y = 1.6 + i * 0.47;
    s.addText(st[0], {
      x: 5.35, y, w: 2.4, h: 0.4, fontSize: 10, color: C.ice, fontFace: FONT_B,
      valign: "middle", margin: 0
    });
    s.addText(st[1], {
      x: 7.8, y, w: 1.6, h: 0.4, fontSize: 11, bold: true, color: C.teal, fontFace: FONT_T,
      valign: "middle", align: "right", margin: 0
    });
  });

  addFooter(s, 23, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 24 · P0 → P8 Roadmap
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 09 · 성능 지표", "P0 → P8 Sprint Roadmap");

  const sprints = [
    ["P0", "평가 정직화", "TimeSeriesSplit — CV std ±0.3→±6.14", C.skyBlue],
    ["P1", "Rotation features", "Test R² 0.10→0.43 (+335%) · Conformal", C.teal],
    ["P2", "Phase-aware anomaly", "Per-phase multiplier · Debounce · ADR-001", C.amber],
    ["P3", "Router 분리 + OTel", "api.py 1120→107라인 · Active Learning 분석", C.coral],
    ["P4+", "Packaging + ADR-002", "pyproject.toml · ChromaDB 95 · CQR · Docker/k8s/CI", C.navy],
    ["P5+", "FAA SWIM 실연동", "Solace SMF/TLS · 219건/60s · ML phase · Per-phase IF", C.skyBlue],
    ["P6", "Feast + Iceberg + AL loop", "Feature Store · Medallion · Grafana 9-panel · 161 chunks", C.teal],
    ["P7", "Bandit + OpenLineage + k8s", "Thompson · Marquez · Argo Rollouts · PSA · NetPol", C.amber],
    ["P8", "NAS 배포 + IaC + Evidence", "Helm/Terraform · Cosign/SBOM · audit + HITL · Runbooks", C.coral],
  ];
  sprints.forEach((sp, i) => {
    const y = 1.0 + i * 0.45;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y, w: 0.8, h: 0.38, fill: { color: sp[3] }, line: { color: sp[3] }
    });
    s.addText(sp[0], {
      x: 0.5, y, w: 0.8, h: 0.38, fontSize: 12, bold: true, color: C.white,
      fontFace: FONT_T, align: "center", valign: "middle", margin: 0
    });
    s.addText(sp[1], {
      x: 1.4, y, w: 2.5, h: 0.38, fontSize: 11, bold: true, color: C.navy,
      fontFace: FONT_T, valign: "middle", margin: 0
    });
    s.addText(sp[2], {
      x: 4.0, y, w: 5.5, h: 0.38, fontSize: 9, color: C.slate, fontFace: FONT_B,
      valign: "middle", margin: 0
    });
  });

  addFooter(s, 24, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 25 · FAA SWIM 실연동 (Hero slide)
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.navy };
  addHeader(s, "CHAPTER 09 · 성능 지표", "🔥 P5+ 하이라이트 · FAA SWIM 실연동");

  // 큰 숫자
  s.addText("219", {
    x: 0.5, y: 1.2, w: 3, h: 1.6, fontSize: 100, bold: true, color: C.amber,
    fontFace: FONT_T, align: "center", margin: 0
  });
  s.addText("건 수신 / 60초", {
    x: 0.5, y: 2.8, w: 3, h: 0.4, fontSize: 14, color: C.white, fontFace: FONT_T,
    align: "center", margin: 0
  });

  // 우측 기술 설명
  s.addText("실제 미 FAA System Wide Information Management 직접 구독", {
    x: 3.8, y: 1.2, w: 5.8, h: 0.4, fontSize: 15, bold: true, color: C.amber,
    fontFace: FONT_T, margin: 0
  });
  s.addText([
    { text: "기술 스택:\n", options: { bold: true, color: C.white, fontSize: 11 } },
    { text: "• Solace PubSub+ SMF over TLS 1.2 \n", options: { color: C.ice, fontSize: 10 } },
    { text: "• ems2.swim.faa.gov:55443 (프로덕션 엔드포인트)\n", options: { color: C.ice, fontSize: 10 } },
    { text: "• AIXM 5.1 XML + FAA event: namespace 파서\n", options: { color: C.ice, fontSize: 10 } },
    { text: "• Q-code → NOTAM class (QNDAS, QMRLC 등)\n", options: { color: C.ice, fontSize: 10 } },
    { text: "• c_rehash TLS trust store (DigiCert G2)\n\n", options: { color: C.ice, fontSize: 10 } },
    { text: "검증 로그: ", options: { bold: true, color: C.teal, fontSize: 11 } },
    { text: "received=219 published=219 parse_err=0", options: { color: C.teal, fontSize: 11, italic: true } },
  ], { x: 3.8, y: 1.65, w: 5.8, h: 3, fontFace: FONT_B, margin: 0 });

  addFooter(s, 25, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 26 · 시연 시나리오
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 10 · 시연 & 마무리", "실시간 데모 5 시나리오");

  const demos = [
    ["📊", "대시보드 진입", "Leaflet 지도에 한반도 상공 항공기 마커 · WebSocket 실시간 업데이트"],
    ["🔥", "NOTAM 라이브", "/notam 페이지 · FAA SWIM 실 데이터 · severity 필터 · Q-code 표시"],
    ["🎯", "지연 예측", "KE081 ICN→CJU · XGBoost 결과 + Conformal 신뢰구간 (6~41분)"],
    ["🚨", "이상 탐지 + AI 분석", "CRUISE 중 고도 급변 감지 → LLM 자동 설명 생성"],
    ["💬", "AI 어시스턴트", "RAG 채팅: 「윈드시어 대응 절차」 → FAA AIM 인용한 한국어 답변"],
  ];
  demos.forEach((d, i) => {
    const y = 1.0 + i * 0.8;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y, w: 0.8, h: 0.7, fill: { color: C.skyBlue }, line: { color: C.skyBlue }
    });
    s.addText(d[0], {
      x: 0.5, y, w: 0.8, h: 0.7, fontSize: 24, color: C.white, fontFace: FONT_T,
      align: "center", valign: "middle", margin: 0
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 1.4, y, w: 8.1, h: 0.7, fill: { color: C.white }, line: { color: C.ice, width: 1 }
    });
    s.addText(d[1], {
      x: 1.55, y: y + 0.05, w: 7.9, h: 0.3, fontSize: 13, bold: true, color: C.navy,
      fontFace: FONT_T, margin: 0
    });
    s.addText(d[2], {
      x: 1.55, y: y + 0.35, w: 7.9, h: 0.35, fontSize: 10, color: C.slate,
      fontFace: FONT_B, margin: 0
    });
  });

  addFooter(s, 26, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 27 · 한계 및 P9+ 계획
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 10 · 시연 & 마무리", "한계 및 P9+ 계획");

  // 좌: 한계
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.0, w: 4.4, h: 3.9, fill: { color: C.white }, line: { color: C.ice, width: 1 }
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.0, w: 4.4, h: 0.45, fill: { color: C.coral }, line: { color: C.coral }
  });
  s.addText("⚠ 현재 한계", {
    x: 0.65, y: 1.08, w: 4.1, h: 0.3, fontSize: 13, bold: true, color: C.white,
    fontFace: FONT_T, margin: 0
  });

  const limits = [
    "학습 데이터 Kaggle 13,969건 (미국 국내선) · 한국 공항 특성 미반영",
    "Isolation Forest F1 0.345 — label 품질 의존 · Active Learning 데이터 누적 필요",
    "LLM vLLM 서빙 시 RTX 3070 에서 40 tok/s (목표 100+ tok/s)",
    "EUROCONTROL NM B2B · KAC 실 API credentials 미보유",
    "Multi-region ADR-003 은 Proposed 상태 (GKE 배포 미완)",
  ];
  limits.forEach((lim, i) => {
    const y = 1.55 + i * 0.62;
    s.addText("• " + lim, {
      x: 0.7, y, w: 4.1, h: 0.55, fontSize: 9, color: C.slate, fontFace: FONT_B, margin: 0
    });
  });

  // 우: P9+
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 1.0, w: 4.4, h: 3.9, fill: { color: C.white }, line: { color: C.ice, width: 1 }
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 1.0, w: 4.4, h: 0.45, fill: { color: C.teal }, line: { color: C.teal }
  });
  s.addText("🚀 P9+ 로드맵", {
    x: 5.25, y: 1.08, w: 4.1, h: 0.3, fontSize: 13, bold: true, color: C.white,
    fontFace: FONT_T, margin: 0
  });

  const plans = [
    "한국공항공사 운항 데이터 수집 → 국내 공항 지연 예측 재학습",
    "Active Learning 실운영 데이터 누적 (3개월) → IF F1 목표 0.85+",
    "vLLM Tensor Parallelism · 멀티 GPU 로 100+ tok/s 달성",
    "EUROCONTROL NM B2B 계약 · ATFM 실시간 CTOT 수신",
    "GCP GKE Phase A 배포 + ADR-003 Multi-region Phase B/C",
    "Kyverno policy · image 서명 admission gate 프로덕션",
  ];
  plans.forEach((p, i) => {
    const y = 1.55 + i * 0.52;
    s.addText("✓ " + p, {
      x: 5.3, y, w: 4.1, h: 0.5, fontSize: 9, color: C.slate, fontFace: FONT_B, margin: 0
    });
  });

  addFooter(s, 27, TOTAL);
}

// ─────────────────────────────────────────────────────────────
// 슬라이드 28 · Q&A
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.navy };
  // 액센트
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.2, h: 5.625, fill: { color: C.skyBlue }, line: { color: C.skyBlue }
  });

  s.addText("Q&A", {
    x: 0.7, y: 1.3, w: 9, h: 1.5, fontSize: 140, bold: true, color: C.skyBlue,
    fontFace: FONT_T, margin: 0
  });
  s.addText("질문과 토론", {
    x: 0.7, y: 2.9, w: 9, h: 0.5, fontSize: 24, color: C.white, fontFace: FONT_T, margin: 0
  });
  s.addText("— 감사합니다 —", {
    x: 0.7, y: 3.5, w: 9, h: 0.4, fontSize: 14, italic: true, color: C.amber,
    fontFace: FONT_T, margin: 0
  });

  // 하단 정보
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 4.7, w: 10, h: 0.92, fill: { color: C.navy }, line: { color: C.navy }
  });
  s.addText([
    { text: "GitHub  ", options: { color: C.amber, fontSize: 11, bold: true } },
    { text: "github.com/biz-doublej/SkyOps-Intelligence\n", options: { color: C.white, fontSize: 11 } },
    { text: "Docs  ", options: { color: C.amber, fontSize: 11, bold: true, breakLine: false } },
    { text: "docs/reproduction_guide.md (564 라인) · docs/adr/ × 3 · docs/runbooks/ × 7\n", options: { color: C.white, fontSize: 11 } },
    { text: "발표자  ", options: { color: C.amber, fontSize: 11, bold: true, breakLine: false } },
    { text: "정재원 (DoubleJ) · jjw050727@naver.com", options: { color: C.white, fontSize: 11 } },
  ], { x: 0.7, y: 4.8, w: 9, h: 0.8, fontFace: FONT_B, margin: 0 });
}

// ─────────────────────────────────────────────────────────────
// 저장
// ─────────────────────────────────────────────────────────────
pres.writeFile({ fileName: "SkyOps_Intelligence_발표자료.pptx" })
  .then(fileName => {
    console.log(`✅ 생성 완료: ${fileName}`);
  })
  .catch(err => {
    console.error("❌ 오류:", err);
    process.exit(1);
  });
