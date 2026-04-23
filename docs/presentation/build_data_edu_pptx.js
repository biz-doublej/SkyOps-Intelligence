// SkyOps Intelligence — 데이터 교육용 PPTX 생성 스크립트
// ========================================================================
// 실행: node build_data_edu_pptx.js
// 출력: SkyOps_Data_교육용_발표자료.pptx
//
// 목적: 외국인 + 한국인 학생을 위한 **데이터 중심** 교육용 슬라이드.
//       각 슬라이드에 한/영 용어, 시각 다이어그램, 단계 번호, before/after
//       비교, speaker notes 를 포함. PowerPoint 에서 추가 애니메이션을
//       걸기 쉽도록 요소별 레이어를 분리해 배치.
//
// pptxgenjs 는 직접 애니메이션 API 가 없지만:
//   - slide.transition = { type, duration } 로 전환 효과
//   - 요소를 레이어로 분리해 두면 PowerPoint 열고 "Animate → Appear" 한 번에 적용 가능

const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "DoubleJ · 정재원";
pres.title = "SkyOps Intelligence — 항공 데이터 교육용 자료";
pres.company = "빅데이터과 캡스톤디자인";

// ── 색상 팔레트 (기존 build_pptx.js 와 동일 · 일관성) ──────────────
const C = {
  navy:    "0B1F3A",
  skyBlue: "1E88E5",
  ice:     "E3F2FD",
  amber:   "FFB300",
  coral:   "EF5350",
  teal:    "00897B",
  slate:   "37474F",
  mute:    "78909C",
  cream:   "FAFAFA",
  white:   "FFFFFF",
  // 교육용 추가 — 학습 단계 색상
  green:   "43A047",
  purple:  "8E24AA",
  orange:  "F57C00",
};

const FONT_T = "Malgun Gothic";
const FONT_B = "Malgun Gothic";
const FONT_M = "Consolas";

const TOTAL = 30;  // 전체 슬라이드 수

// ─────────────────────────────────────────────────────────────────
// 공통 헬퍼
// ─────────────────────────────────────────────────────────────────
function addFooter(slide, pageNum) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 5.35, w: 10, h: 0.28, fill: { color: C.navy }, line: { color: C.navy },
  });
  slide.addText("SkyOps Intelligence · 데이터 교육용 자료 · 2026-04-19", {
    x: 0.3, y: 5.37, w: 6, h: 0.24, fontSize: 9, color: C.ice, fontFace: FONT_B, margin: 0,
  });
  slide.addText(`${pageNum} / ${TOTAL}`, {
    x: 9.0, y: 5.37, w: 0.8, h: 0.24, fontSize: 9, color: C.ice, fontFace: FONT_B,
    align: "right", margin: 0,
  });
}

function addHeader(slide, chapterEn, titleKo, titleEn) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.85, fill: { color: C.cream }, line: { color: C.cream },
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: 0.85, fill: { color: C.skyBlue }, line: { color: C.skyBlue },
  });
  slide.addText(chapterEn, {
    x: 0.3, y: 0.04, w: 9.5, h: 0.25, fontSize: 10, color: C.mute, fontFace: FONT_T,
    bold: false, margin: 0, charSpacing: 4,
  });
  slide.addText(titleKo, {
    x: 0.3, y: 0.27, w: 9.5, h: 0.38, fontSize: 22, color: C.navy, fontFace: FONT_T,
    bold: true, margin: 0,
  });
  slide.addText(titleEn, {
    x: 0.3, y: 0.63, w: 9.5, h: 0.18, fontSize: 10.5, color: C.slate, fontFace: FONT_B,
    italic: true, margin: 0,
  });
}

function numberedCircle(slide, n, x, y, color = C.skyBlue) {
  slide.addShape(pres.shapes.OVAL, {
    x, y, w: 0.55, h: 0.55, fill: { color }, line: { color },
  });
  slide.addText(String(n), {
    x, y, w: 0.55, h: 0.55, fontSize: 22, bold: true, color: C.white,
    fontFace: FONT_T, align: "center", valign: "middle", margin: 0,
  });
}

function connector(slide, x1, y1, x2, y2, color = C.mute) {
  slide.addShape(pres.shapes.LINE, {
    x: x1, y: y1, w: x2 - x1, h: y2 - y1,
    line: { color, width: 2, endArrowType: "triangle" },
  });
}

function koEnText(slide, x, y, w, h, ko, en, opts = {}) {
  slide.addText([
    { text: ko, options: { bold: true, color: opts.color || C.navy, fontSize: opts.size || 14 } },
    { text: "   " + en, options: { color: C.mute, fontSize: (opts.size || 14) - 2, italic: true } },
  ], {
    x, y, w, h, fontFace: FONT_B, margin: 0, valign: "middle",
  });
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 1 · 표지
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.navy };
  s.transition = { type: "fade" };

  // 장식 — 크로스헤어/레이더 모티프
  s.addShape(pres.shapes.OVAL, {
    x: 7.5, y: 0.3, w: 2.2, h: 2.2, fill: { type: "none" },
    line: { color: C.skyBlue, width: 1, dashType: "dash" },
  });
  s.addShape(pres.shapes.OVAL, {
    x: 8.0, y: 0.8, w: 1.2, h: 1.2, fill: { type: "none" },
    line: { color: C.amber, width: 1 },
  });
  s.addText("🛫", {
    x: 7.5, y: 0.3, w: 2.2, h: 2.2, fontSize: 60, color: C.white,
    align: "center", valign: "middle", fontFace: FONT_T, margin: 0,
  });

  s.addText("DATA · EDUCATION · AVIATION", {
    x: 0.5, y: 0.6, w: 9, h: 0.3, fontSize: 12, color: C.amber,
    fontFace: FONT_T, bold: true, charSpacing: 8,
  });
  s.addText("항공 데이터 이야기", {
    x: 0.5, y: 1.2, w: 9, h: 0.9, fontSize: 44, color: C.white,
    fontFace: FONT_T, bold: true,
  });
  s.addText("Aviation Data Story — from Raw to Model", {
    x: 0.5, y: 2.15, w: 9, h: 0.45, fontSize: 20, color: C.ice,
    fontFace: FONT_B, italic: true,
  });
  s.addText([
    { text: "데이터가 어떻게 ", options: { color: C.ice } },
    { text: "수집", options: { color: C.amber, bold: true } },
    { text: "되고 ", options: { color: C.ice } },
    { text: "정제", options: { color: C.amber, bold: true } },
    { text: "되고 ", options: { color: C.ice } },
    { text: "모델", options: { color: C.amber, bold: true } },
    { text: "이 되는가", options: { color: C.ice } },
  ], {
    x: 0.5, y: 2.7, w: 9, h: 0.4, fontSize: 16, fontFace: FONT_B,
  });
  s.addText("How data is collected, transformed, and turned into models", {
    x: 0.5, y: 3.15, w: 9, h: 0.3, fontSize: 12, color: C.mute,
    fontFace: FONT_B, italic: true,
  });

  // 하단 메타
  s.addShape(pres.shapes.LINE, {
    x: 0.5, y: 4.2, w: 9, h: 0, line: { color: C.skyBlue, width: 1 },
  });
  s.addText([
    { text: "DoubleJ 팀 / 정재원", options: { bold: true, color: C.white } },
    { text: "   ·   ", options: { color: C.mute } },
    { text: "빅데이터과 캡스톤디자인", options: { color: C.ice } },
    { text: "   ·   ", options: { color: C.mute } },
    { text: "2026-04-19 (v2.2.0)", options: { color: C.amber } },
  ], {
    x: 0.5, y: 4.4, w: 9, h: 0.3, fontSize: 12, fontFace: FONT_B,
  });
  s.addText("SkyOps Intelligence · GitHub: biz-doublej/SkyOps-Intelligence", {
    x: 0.5, y: 4.75, w: 9, h: 0.3, fontSize: 10, color: C.mute,
    fontFace: FONT_B, italic: true,
  });

  s.addNotes(
    "안녕하세요. 빅데이터과 3 학년 정재원입니다. 오늘은 제가 속한 DoubleJ 팀이 만든 SkyOps Intelligence 프로젝트의 데이터 이야기를 해보려 합니다. " +
    "이 프로젝트에서 데이터가 어떻게 수집되고, 어떻게 가공되고, 최종적으로 모델이 되는지를 중심으로 설명드리겠습니다. " +
    "앞으로 30 장 동안, 여러분은 '원본 데이터 한 줄이 어떻게 관제사 화면의 알림 하나가 되는가' 라는 질문에 대한 답을 찾게 되실 겁니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 2 · 학습 목표
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  s.transition = { type: "push" };
  addHeader(s, "CHAPTER 01 · ORIENTATION", "학습 목표", "Learning Objectives — what you will know after this talk");

  const goals = [
    ["항공 데이터가 어떻게 생성되는가", "How aviation data is generated", C.skyBlue],
    ["Raw 데이터를 어떻게 정제하는가", "How to clean raw data", C.teal],
    ["왜 시계열 분할이 중요한가", "Why time-ordered split matters (temporal leakage)", C.amber],
    ["Feature Engineering 이 모델을 어떻게 바꾸는가 (실제 사례: R² +335%)",
     "How feature engineering transforms models (real case: R² +335%)", C.purple],
    ["XGBoost / Isolation Forest 가 왜 선택됐는가",
     "Why XGBoost / Isolation Forest were the right choice", C.coral],
  ];

  goals.forEach(([ko, en, col], i) => {
    const y = 1.15 + i * 0.72;
    numberedCircle(s, i + 1, 0.6, y, col);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 1.35, y, w: 8.2, h: 0.55, fill: { color: C.white },
      line: { color: col, width: 1.5 }, rectRadius: 0.08,
    });
    s.addText(ko, {
      x: 1.5, y: y + 0.02, w: 8, h: 0.28, fontSize: 13, bold: true,
      color: C.navy, fontFace: FONT_T, margin: 0,
    });
    s.addText(en, {
      x: 1.5, y: y + 0.28, w: 8, h: 0.24, fontSize: 10, italic: true,
      color: C.mute, fontFace: FONT_B, margin: 0,
    });
  });

  addFooter(s, 2);
  s.addNotes(
    "이 발표가 끝났을 때 여러분이 다섯 가지를 이해하시도록 구성했습니다. " +
    "먼저 항공 데이터가 어떻게 생성되는지를 살펴보고, 이어서 raw 데이터를 어떻게 정제하는지, " +
    "그리고 왜 시계열 분할이 중요한지와 temporal leakage 가 무엇인지를 다루겠습니다. " +
    "그다음으로 Feature Engineering 이 모델을 어떻게 바꾸는지를 실제 사례 R² 335 퍼센트 개선 사례로 보여드리고, " +
    "마지막으로 XGBoost 와 Isolation Forest 가 왜 선택됐는지 그 이유를 설명드립니다. " +
    "특히 세 번째와 네 번째가 가장 중요합니다. 이 두 가지는 실제로 제가 진행한 프로젝트의 P0, P1 스프린트에서 숫자로 증명된 내용이라, 숫자 자체를 꼭 기억해 두시면 좋겠습니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 3 · 데이터란 무엇인가?
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  s.transition = { type: "wipe" };
  addHeader(s, "CHAPTER 02 · BASICS", "데이터란 무엇인가?", "What is Data? — from measurement to model");

  s.addText("📐", {
    x: 0.5, y: 1.1, w: 0.9, h: 0.9, fontSize: 42, fontFace: FONT_T,
    align: "center", valign: "middle", margin: 0,
  });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 1.55, y: 1.15, w: 8.0, h: 0.9, fill: { color: C.ice },
    line: { color: C.skyBlue, width: 1 }, rectRadius: 0.08,
  });
  s.addText([
    { text: "데이터 = 세상의 측정값\n",
      options: { fontSize: 16, bold: true, color: C.navy } },
    { text: "Data = quantified observations of the world",
      options: { fontSize: 11, italic: true, color: C.slate } },
  ], {
    x: 1.7, y: 1.2, w: 7.7, h: 0.8, fontFace: FONT_B, margin: 0, valign: "middle",
  });

  // Two parallel examples — medical vs aviation
  const examples = [
    {
      title: "의료 (Medical)", x: 0.5, color: C.coral,
      chain: ["체온계", "37.5°C", "EHR DB", "진단 모델"],
      chainEn: ["thermometer", "numeric", "database", "diagnosis model"],
    },
    {
      title: "항공 (Aviation)", x: 5.2, color: C.skyBlue,
      chain: ["레이더 수신기", "위도/경도", "Kafka 스트림", "지연 예측"],
      chainEn: ["radar receiver", "lat/lon", "Kafka stream", "delay prediction"],
    },
  ];

  examples.forEach((ex) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: ex.x, y: 2.3, w: 4.3, h: 2.8, fill: { color: C.white },
      line: { color: ex.color, width: 2 }, rectRadius: 0.1,
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: ex.x, y: 2.3, w: 4.3, h: 0.4, fill: { color: ex.color }, line: { color: ex.color },
    });
    s.addText(ex.title, {
      x: ex.x, y: 2.3, w: 4.3, h: 0.4, fontSize: 13, bold: true, color: C.white,
      fontFace: FONT_T, align: "center", valign: "middle", margin: 0,
    });

    ex.chain.forEach((step, i) => {
      const y = 2.85 + i * 0.53;
      // 박스 (wider cell so Korean/English don't overlap)
      s.addShape(pres.shapes.RECTANGLE, {
        x: ex.x + 0.2, y, w: 3.9, h: 0.4, fill: { color: C.ice },
        line: { color: ex.color, width: 1 },
      });
      // 한글 라벨 — 왼쪽 고정 폭
      s.addText(step, {
        x: ex.x + 0.3, y, w: 2.0, h: 0.4, fontSize: 11, bold: true,
        color: C.navy, fontFace: FONT_T, margin: 0, valign: "middle",
      });
      // 영문 — 우측 끝까지
      s.addText(ex.chainEn[i], {
        x: ex.x + 2.35, y, w: 1.75, h: 0.4, fontSize: 9,
        color: C.mute, italic: true, fontFace: FONT_B, margin: 0, valign: "middle",
        align: "right",
      });
      // 화살표 — 박스 바깥 아래, 다음 박스 위로 안 넘어가게
      if (i < ex.chain.length - 1) {
        s.addShape(pres.shapes.LINE, {
          x: ex.x + 2.0, y: y + 0.42, w: 0, h: 0.08,
          line: { color: ex.color, width: 2, endArrowType: "triangle" },
        });
      }
    });
  });

  addFooter(s, 3);
  s.addNotes(
    "잠깐 기본으로 돌아가 보겠습니다. 데이터란 무엇일까요. 한마디로 말씀드리면, 데이터는 세상의 측정값입니다. " +
    "의료에서는 체온계가 숫자를 만들고 EHR 데이터베이스를 거쳐 진단 모델로 흘러가고, " +
    "항공에서는 레이더 수신기가 위도와 경도를 측정해서 Kafka 스트림을 거쳐 지연 예측 모델로 들어갑니다. " +
    "센서, 숫자, 저장, 모델이라는 네 단계 구조는 어떤 도메인에서도 똑같이 반복됩니다. " +
    "이 프레임을 머릿속에 두시면, 앞으로 나올 모든 슬라이드가 이 구조 안에 들어맞게 됩니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 4 · 항공 데이터의 특성
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  s.transition = { type: "wipe" };
  addHeader(s, "CHAPTER 02 · BASICS", "항공 데이터의 특성", "4 Characteristics of Aviation Data");

  const chars = [
    { icon: "⏱", ko: "실시간", en: "Real-time", desc: "초 단위 갱신\nupdates in seconds",
      color: C.coral, x: 0.5, y: 1.1 },
    { icon: "🚀", ko: "고빈도", en: "High frequency", desc: "초당 수천 건\nthousands/sec",
      color: C.amber, x: 5.2, y: 1.1 },
    { icon: "📈", ko: "시계열", en: "Time-series", desc: "순서가 중요\norder matters",
      color: C.teal, x: 0.5, y: 3.1 },
    { icon: "🌐", ko: "다중 소스", en: "Multi-source", desc: "레이더+기상+관제\nradar+weather+ATC",
      color: C.skyBlue, x: 5.2, y: 3.1 },
  ];

  chars.forEach((c) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: c.x, y: c.y, w: 4.3, h: 1.85, fill: { color: C.white },
      line: { color: c.color, width: 2 }, rectRadius: 0.12,
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: c.x, y: c.y, w: 0.12, h: 1.85, fill: { color: c.color }, line: { color: c.color },
    });
    s.addText(c.icon, {
      x: c.x + 0.3, y: c.y + 0.2, w: 0.9, h: 0.9, fontSize: 38,
      fontFace: FONT_T, align: "center", valign: "middle", margin: 0,
    });
    s.addText(c.ko, {
      x: c.x + 1.35, y: c.y + 0.2, w: 2.8, h: 0.4, fontSize: 20, bold: true,
      color: C.navy, fontFace: FONT_T, margin: 0,
    });
    s.addText(c.en, {
      x: c.x + 1.35, y: c.y + 0.6, w: 2.8, h: 0.28, fontSize: 10, italic: true,
      color: C.mute, fontFace: FONT_B, margin: 0,
    });
    s.addText(c.desc, {
      x: c.x + 1.35, y: c.y + 0.95, w: 2.8, h: 0.8, fontSize: 11,
      color: C.slate, fontFace: FONT_B, margin: 0,
    });
  });

  addFooter(s, 4);
  s.addNotes(
    "항공 데이터에는 네 가지 특별한 성질이 있습니다. " +
    "첫째는 실시간 성질로 초 단위로 업데이트되기 때문에 1 분의 지연도 큰 의미를 갖고, 둘째는 고빈도 성질로 초당 수천 건이 쏟아져 들어옵니다. " +
    "셋째는 시계열 성질인데 순서가 매우 중요해서 절대로 섞으면 안 되고, 넷째는 다중 소스 성질로 레이더와 기상, 관제 메시지가 모두 합쳐져야 비로소 의미가 생깁니다. " +
    "이 네 가지 성질이 바로 아무 데이터나 아무 방식으로 쓰면 안 되는 이유입니다. " +
    "실시간과 고빈도 때문에 Kafka 가 필요하고, 시계열이기 때문에 절대 shuffle 을 하면 안 되며, 다중 소스이기 때문에 Schema Registry 라는 계약이 필요합니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 5 · 4개 데이터 소스 개요
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 03 · DATA SOURCES", "4 개의 데이터 소스", "Four Data Sources at a Glance");

  const srcs = [
    { num: 1, ko: "OpenSky Network", en: "ADS-B receiver network (crowdsourced)",
      detail: "35,000 수신기 · 10초/폴링\n35k receivers · 10s polling", color: C.skyBlue },
    { num: 2, ko: "NOAA + KMA METAR", en: "Airport weather reports",
      detail: "30분 주기 · 공항 기상\n30-min · airport weather", color: C.teal },
    { num: 3, ko: "FAA SWIM ★", en: "Solace JMS · TLS 1.2 · AIXM XML",
      detail: "60초 / 219건 검증\n60s / 219 NOTAMs verified", color: C.amber },
    { num: 4, ko: "Kaggle flights.csv", en: "US DOT BTS 2015 batch dataset",
      detail: "5.7M 행 · 31 컬럼\n5.7M rows · 31 cols", color: C.purple },
  ];

  srcs.forEach((src, i) => {
    const y = 1.15 + i * 1.02;
    numberedCircle(s, src.num, 0.55, y + 0.1, src.color);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 1.35, y, w: 8.2, h: 0.85, fill: { color: C.white },
      line: { color: src.color, width: 1.5 }, rectRadius: 0.08,
    });
    s.addText(src.ko, {
      x: 1.5, y: y + 0.05, w: 4, h: 0.35, fontSize: 15, bold: true, color: C.navy,
      fontFace: FONT_T, margin: 0,
    });
    s.addText(src.en, {
      x: 1.5, y: y + 0.42, w: 4, h: 0.28, fontSize: 10, italic: true, color: C.mute,
      fontFace: FONT_B, margin: 0,
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 5.8, y: y + 0.12, w: 3.6, h: 0.6, fill: { color: C.ice }, line: { color: C.ice },
    });
    s.addText(src.detail, {
      x: 5.9, y: y + 0.14, w: 3.5, h: 0.58, fontSize: 10, color: C.slate,
      fontFace: FONT_B, margin: 0, valign: "middle",
    });
  });

  s.addText("★ FAA SWIM 은 대학 프로젝트로서 드문 공식 프로덕션 연동", {
    x: 1.35, y: 5.03, w: 8.2, h: 0.25, fontSize: 9.5, italic: true, color: C.amber,
    fontFace: FONT_B, bold: true, margin: 0,
  });

  addFooter(s, 5);
  s.addNotes(
    "저는 이 프로젝트에서 총 네 가지 데이터 소스를 사용하고 있습니다. " +
    "첫 번째는 OpenSky Network 로 전 세계 3만 5천 개 지상 수신기가 기여하는 공개 ADS-B 네트워크이고 10 초마다 항공기 위치가 업데이트됩니다. " +
    "두 번째는 NOAA 와 KMA 의 METAR 데이터로 공항 기상 보고서이고 30 분 주기로 갱신되며, " +
    "세 번째가 FAA SWIM 으로 미 연방항공청의 공식 System Wide Information Management 데이터입니다. " +
    "네 번째는 Kaggle 의 flights.csv 로 오백칠십만 행 규모의 2015 년 배치 데이터입니다. " +
    "별표가 붙은 SWIM 은 제가 이 프로젝트에서 가장 자랑스럽게 생각하는 플래그십 성과입니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 6 · OpenSky ADS-B 자세히
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 03 · DATA SOURCES", "OpenSky ADS-B 작동 원리", "How ADS-B Works");

  // ADS-B flow diagram
  // 비행기 → 방송 → 수신기 → OpenSky → 수집기
  const stages = [
    { icon: "✈️", ko: "항공기", en: "Aircraft", x: 0.5 },
    { icon: "📡", ko: "지상 수신기", en: "Ground receiver", x: 2.7 },
    { icon: "🌐", ko: "OpenSky 서버", en: "OpenSky API", x: 4.9 },
    { icon: "📨", ko: "Kafka 토픽", en: "flight-position", x: 7.1 },
  ];
  stages.forEach((st, i) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: st.x, y: 1.1, w: 1.9, h: 1.6, fill: { color: C.white },
      line: { color: C.skyBlue, width: 1.5 }, rectRadius: 0.08,
    });
    s.addText(st.icon, {
      x: st.x, y: 1.2, w: 1.9, h: 0.6, fontSize: 36, align: "center", valign: "middle",
      fontFace: FONT_T, margin: 0,
    });
    s.addText(st.ko, {
      x: st.x, y: 1.85, w: 1.9, h: 0.35, fontSize: 12.5, bold: true, color: C.navy,
      fontFace: FONT_T, align: "center", margin: 0,
    });
    s.addText(st.en, {
      x: st.x, y: 2.22, w: 1.9, h: 0.3, fontSize: 9.5, italic: true, color: C.mute,
      fontFace: FONT_B, align: "center", margin: 0,
    });
    if (i < stages.length - 1) {
      s.addText("→", {
        x: st.x + 1.9, y: 1.1, w: 0.3, h: 1.6, fontSize: 24, color: C.amber,
        bold: true, align: "center", valign: "middle", margin: 0,
      });
    }
  });

  // "무엇이 들어오나" 필드 표
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 3.0, w: 8.9, h: 2.0, fill: { color: C.white },
    line: { color: C.slate, width: 1 }, rectRadius: 0.08,
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 3.0, w: 8.9, h: 0.38, fill: { color: C.navy }, line: { color: C.navy },
  });
  s.addText("한 편의 항공기에서 들어오는 17개 필드 (What arrives per aircraft)", {
    x: 0.5, y: 3.0, w: 8.9, h: 0.38, fontSize: 11.5, bold: true, color: C.white,
    fontFace: FONT_T, align: "center", valign: "middle", margin: 0,
  });

  // 3-column layout of field samples
  const fields = [
    ["icao24", "aa1234", "ICAO 24-bit hex"],
    ["callsign", "KAL123", "콜사인 / call sign"],
    ["latitude", "37.46°", "위도 / latitude"],
    ["longitude", "126.44°", "경도 / longitude"],
    ["baro_altitude", "10,668 m", "기압 고도 / altitude"],
    ["velocity", "245 m/s", "대지속도 / ground speed"],
    ["vertical_rate", "-2.6 m/s", "수직속도 / climb rate"],
    ["on_ground", "false", "지상 여부 / on ground"],
    ["squawk", "2134", "Squawk 코드"],
  ];
  fields.forEach((f, i) => {
    const col = i % 3;
    const row = Math.floor(i / 3);
    const x = 0.6 + col * 2.95;
    const y = 3.48 + row * 0.48;
    s.addText([
      { text: f[0], options: { color: C.skyBlue, bold: true, fontFace: FONT_M, fontSize: 10 } },
      { text: " = " + f[1] + "\n", options: { color: C.amber, fontFace: FONT_M, fontSize: 10 } },
      { text: f[2], options: { color: C.mute, italic: true, fontSize: 8.5 } },
    ], {
      x, y, w: 2.9, h: 0.45, fontFace: FONT_B, margin: 0,
    });
  });

  addFooter(s, 6);
  s.addNotes(
    "ADS-B 는 Automatic Dependent Surveillance-Broadcast 의 약자입니다. " +
    "항공기가 자기 위치를 스스로 방송하면 지상 수신기가 받아서 OpenSky 서버의 API 로 전송합니다. " +
    "제가 작성한 수집기가 30 초마다 OpenSky API 를 폴링해서 Kafka 의 flight-position 토픽으로 publish 하도록 구현했습니다. " +
    "항공기 한 편당 업데이트마다 17 개 필드가 들어오고, 전 세계 3만 5천 대의 수신기가 대부분 자원봉사자에 의해 운영됩니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 7 · METAR 해독 실습
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 03 · DATA SOURCES", "METAR 해독 · 실습", "Decoding a METAR — live example");

  // 원본 METAR
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 1.05, w: 8.9, h: 0.9, fill: { color: C.navy }, line: { color: C.navy }, rectRadius: 0.1,
  });
  s.addText("📡  원본 (Raw METAR)", {
    x: 0.7, y: 1.1, w: 3, h: 0.3, fontSize: 11, bold: true, color: C.amber, fontFace: FONT_T, margin: 0,
  });
  s.addText("RKSI 030900Z 29012KT 9999 SCT030 08/M02 Q1020", {
    x: 0.7, y: 1.38, w: 8.5, h: 0.5, fontSize: 18, color: C.white,
    fontFace: FONT_M, bold: true, margin: 0,
  });

  // 토큰 분해
  const tokens = [
    { tok: "RKSI",      ko: "인천공항 ICAO 코드",    en: "Incheon ICAO code",     color: C.skyBlue },
    { tok: "030900Z",   ko: "3일 09:00 UTC 관측",    en: "day-03 09:00 UTC",      color: C.teal },
    { tok: "29012KT",   ko: "풍향 290°, 12 노트",    en: "wind 290°, 12 knots",   color: C.amber },
    { tok: "9999",      ko: "가시거리 10 km 이상",   en: "visibility ≥10 km",     color: C.green },
    { tok: "SCT030",    ko: "3000 ft 에 부분운",     en: "scattered clouds @3000ft", color: C.purple },
    { tok: "08/M02",    ko: "기온 8°C / 이슬점 -2°C", en: "temp 8°C / dew -2°C",  color: C.coral },
    { tok: "Q1020",     ko: "QNH 1020 hPa",          en: "altimeter 1020 hPa",    color: C.slate },
  ];

  tokens.forEach((t, i) => {
    const y = 2.2 + i * 0.45;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y, w: 1.7, h: 0.38, fill: { color: t.color }, line: { color: t.color },
    });
    s.addText(t.tok, {
      x: 0.5, y, w: 1.7, h: 0.38, fontSize: 12, bold: true, color: C.white,
      fontFace: FONT_M, align: "center", valign: "middle", margin: 0,
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 2.2, y, w: 7.2, h: 0.38, fill: { color: C.white }, line: { color: t.color, width: 0.5 },
    });
    s.addText([
      { text: t.ko, options: { bold: true, color: C.navy, fontSize: 11 } },
      { text: "   " + t.en, options: { italic: true, color: C.mute, fontSize: 9 } },
    ], {
      x: 2.35, y, w: 7.0, h: 0.38, fontFace: FONT_B, margin: 0, valign: "middle",
    });
  });

  addFooter(s, 7);
  s.addNotes(
    "두 번째 소스인 METAR 기상 보고서는 처음 보면 암호처럼 보이지만 함께 해독해 보면 어렵지 않습니다. " +
    "한 줄의 METAR 가 일곱 개의 토큰으로 분해되는데, RKSI 는 인천공항 ICAO 코드, 030900Z 는 3 일 09 시 UTC 관측, " +
    "29012KT 는 풍향 290 도 풍속 12 노트, 9999 는 가시거리 10 킬로미터 이상, SCT030 은 3000 피트에 부분운, " +
    "08/M02 는 기온 8 도 이슬점 영하 2 도, Q1020 은 QNH 1020 헥토파스칼을 뜻합니다. " +
    "이 포맷은 국제 항공 표준이라 전 세계가 공통으로 사용하고, 제가 작성한 파서가 이 문자열을 JSON 으로 파싱하고 다시 Avro 로 변환해 Kafka 에 넣습니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 8 · FAA SWIM 실연동 (플래그십 성과)
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 03 · DATA SOURCES", "FAA SWIM 실연동 ★", "FAA SWIM Live Integration — our flagship achievement");

  // 배지
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 6.7, y: 1.0, w: 2.7, h: 1.3, fill: { color: C.amber }, line: { color: C.amber }, rectRadius: 0.15,
  });
  s.addText("60 초 / 219건", {
    x: 6.7, y: 1.05, w: 2.7, h: 0.45, fontSize: 18, bold: true, color: C.navy,
    fontFace: FONT_T, align: "center", margin: 0,
  });
  s.addText("parse_err = 0", {
    x: 6.7, y: 1.48, w: 2.7, h: 0.35, fontSize: 12, bold: true, color: C.navy,
    fontFace: FONT_M, align: "center", margin: 0,
  });
  s.addText("production verified", {
    x: 6.7, y: 1.83, w: 2.7, h: 0.3, fontSize: 9.5, italic: true, color: C.navy,
    fontFace: FONT_B, align: "center", margin: 0,
  });

  // Flow
  const stages = [
    { ko: "FAA Solace\nJMS Broker", en: "ems2.swim.faa.gov:55443", color: C.navy, x: 0.5 },
    { ko: "TLS 1.2\n인증 통과", en: "DigiCert Global Root G2", color: C.coral, x: 2.6 },
    { ko: "AIXM 5.1\nXML 파싱", en: "FAA event: namespace", color: C.teal, x: 4.7 },
    { ko: "Kafka\nnotam 토픽", en: "Avro v2.0 schema", color: C.skyBlue, x: 6.8 },
  ];
  stages.forEach((st, i) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: st.x, y: 2.55, w: 1.9, h: 1.0, fill: { color: st.color }, line: { color: st.color }, rectRadius: 0.08,
    });
    s.addText(st.ko, {
      x: st.x, y: 2.6, w: 1.9, h: 0.55, fontSize: 11, bold: true, color: C.white,
      fontFace: FONT_T, align: "center", margin: 0,
    });
    s.addText(st.en, {
      x: st.x + 0.05, y: 3.17, w: 1.8, h: 0.35, fontSize: 8, italic: true, color: C.ice,
      fontFace: FONT_M, align: "center", margin: 0,
    });
    if (i < stages.length - 1) {
      s.addText("→", {
        x: st.x + 1.9, y: 2.55, w: 0.22, h: 1.0, fontSize: 22, bold: true, color: C.amber,
        align: "center", valign: "middle", margin: 0,
      });
    }
  });

  // 왜 어려웠나
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 3.85, w: 8.9, h: 1.3, fill: { color: C.ice }, line: { color: C.coral, width: 1.5 }, rectRadius: 0.08,
  });
  s.addText("왜 어려웠나 (Why it was hard)", {
    x: 0.7, y: 3.92, w: 8.6, h: 0.3, fontSize: 12, bold: true, color: C.coral, fontFace: FONT_T, margin: 0,
  });
  s.addText([
    { text: "• Trust store setup 3 번 실패 후 성공  ", options: { color: C.navy, fontSize: 10, bold: true } },
    { text: "(3 failed attempts at trust store setup)\n", options: { color: C.mute, fontSize: 9, italic: true } },
    { text: "• DigiCert Global Root G2 인증서를 수동으로 ", options: { color: C.navy, fontSize: 10 } },
    { text: "c_rehash ", options: { color: C.amber, fontSize: 10, fontFace: FONT_M, bold: true } },
    { text: "형식으로 import\n", options: { color: C.navy, fontSize: 10 } },
    { text: "  (manually imported DigiCert G2 in c_rehash format)\n", options: { color: C.mute, fontSize: 9, italic: true } },
    { text: "• AIXM 5.1 XML + FAA event: namespace 파서 자체 구현 ", options: { color: C.navy, fontSize: 10 } },
    { text: "(custom parser)", options: { color: C.mute, fontSize: 9, italic: true } },
  ], {
    x: 0.7, y: 4.25, w: 8.6, h: 0.88, fontFace: FONT_B, margin: 0,
  });

  addFooter(s, 8);
  s.addNotes(
    "이 프로젝트에서 제가 가장 자랑스럽게 생각하는 플래그십 성과라 슬라이드 한 장을 통째로 썼습니다. " +
    "미 연방항공청의 프로덕션 브로커에 직접 연결해서 60 초 안에 실제 NOTAM 219 건을 파싱 에러 0 건으로 수신했습니다. " +
    "대학 캡스톤 프로젝트로서는 극히 드문 성과인데, 일반 REST API 가 아니라 Solace JMS 프로토콜을 써야 하고, TLS 1.2 인증서 검증이 필수이며, AIXM 5.1 표준 XML 파서를 직접 구현해야 했기 때문입니다. " +
    "trust store 셋업을 세 번 연속 실패하고 네 번째에 성공했고, DigiCert Global Root G2 인증서를 수동으로 c_rehash 형식으로 import 하고 나서야 해결할 수 있었습니다. " +
    "학부생 신분으로도 이런 인프라 수준의 integration 에 도전할 수 있다는 것을 보여드리고 싶어 실패 과정까지 공유드렸습니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 9 · Kaggle flights.csv EDA
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 03 · DATA SOURCES", "Kaggle flights.csv · EDA", "Exploring the 5.7M row training dataset");

  // 좌측 데이터 규모
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 1.05, w: 4.2, h: 1.7, fill: { color: C.navy }, line: { color: C.navy }, rectRadius: 0.1,
  });
  s.addText("📦  데이터 규모", {
    x: 0.6, y: 1.1, w: 4.0, h: 0.3, fontSize: 12, bold: true, color: C.amber, fontFace: FONT_T, margin: 0,
  });
  s.addText("5.7 M", {
    x: 0.6, y: 1.42, w: 2, h: 0.65, fontSize: 38, bold: true, color: C.white, fontFace: FONT_T, margin: 0,
  });
  s.addText("행\nrows", {
    x: 2.3, y: 1.52, w: 1, h: 0.6, fontSize: 10, color: C.ice, fontFace: FONT_B, margin: 0, valign: "middle",
  });
  s.addText("31 컬럼 · 580 MB", {
    x: 0.6, y: 2.12, w: 4, h: 0.28, fontSize: 10, color: C.ice, fontFace: FONT_B, margin: 0,
  });
  s.addText("US DOT BTS 2015 · 10% → 500K 샘플링", {
    x: 0.6, y: 2.42, w: 4, h: 0.28, fontSize: 9, italic: true, color: C.mute, fontFace: FONT_B, margin: 0,
  });

  // 우측 EDA 지표
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 4.9, y: 1.05, w: 4.5, h: 1.7, fill: { color: C.white }, line: { color: C.skyBlue, width: 1 }, rectRadius: 0.1,
  });
  s.addText("📊  EDA 핵심 지표", {
    x: 5.0, y: 1.1, w: 4.3, h: 0.3, fontSize: 12, bold: true, color: C.skyBlue, fontFace: FONT_T, margin: 0,
  });
  const kpis = [
    ["지연 편 (>0 분)", "38.8%", "delayed flights"],
    ["취소 편", "3.4%", "cancelled"],
    ["평균 도착 지연", "6.2 분", "mean arr delay"],
    ["최대 지연", "1,971 분", "worst case (32+ hrs)"],
  ];
  kpis.forEach((k, i) => {
    const y = 1.45 + i * 0.3;
    s.addText(k[0], {
      x: 5.0, y, w: 1.8, h: 0.27, fontSize: 9.5, color: C.slate, fontFace: FONT_B, margin: 0,
    });
    s.addText(k[1], {
      x: 6.8, y, w: 1.1, h: 0.27, fontSize: 11.5, bold: true, color: C.coral,
      fontFace: FONT_T, align: "right", margin: 0,
    });
    s.addText(k[2], {
      x: 7.95, y: y + 0.03, w: 1.4, h: 0.25, fontSize: 8.5, italic: true, color: C.mute,
      fontFace: FONT_B, margin: 0,
    });
  });

  // 지연 원인별 비율 막대그래프 (pure shape)
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 2.95, w: 8.9, h: 2.2, fill: { color: C.white }, line: { color: C.slate, width: 1 }, rectRadius: 0.08,
  });
  s.addText("지연 원인별 기여도 (Delay Cause Attribution)", {
    x: 0.7, y: 3.0, w: 8.6, h: 0.3, fontSize: 12, bold: true, color: C.navy, fontFace: FONT_T, margin: 0,
  });
  const causes = [
    { ko: "전편 지연 (Cascade)", en: "Late aircraft (reactionary)", pct: 39.6, color: C.coral },
    { ko: "항공사 귀책",          en: "Carrier",                  pct: 31.2, color: C.amber },
    { ko: "국가항공시스템 NAS",   en: "National Air System",      pct: 23.3, color: C.skyBlue },
    { ko: "기상",                  en: "Weather",                  pct: 5.7,  color: C.teal },
    { ko: "보안",                  en: "Security",                 pct: 0.1,  color: C.mute },
  ];
  const maxWidth = 5.5;
  causes.forEach((c, i) => {
    const y = 3.4 + i * 0.32;
    s.addText(c.ko, {
      x: 0.7, y, w: 2.3, h: 0.3, fontSize: 9.5, bold: true, color: C.navy,
      fontFace: FONT_T, margin: 0,
    });
    const w = (c.pct / 40) * maxWidth;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 3.1, y: y + 0.04, w, h: 0.22, fill: { color: c.color }, line: { color: c.color },
    });
    s.addText(c.pct + "%", {
      x: 3.1 + w + 0.1, y, w: 0.8, h: 0.3, fontSize: 10, bold: true, color: c.color,
      fontFace: FONT_T, margin: 0,
    });
    s.addText(c.en, {
      x: 8.0, y: y + 0.04, w: 1.4, h: 0.25, fontSize: 8.5, italic: true, color: C.mute,
      fontFace: FONT_B, align: "right", margin: 0,
    });
  });
  s.addText("💡 전편 지연 39.6% → Rotation features 5 종 추가의 근거 (P1 · 슬라이드 16)", {
    x: 0.7, y: 4.85, w: 8.6, h: 0.25, fontSize: 9, italic: true, bold: true, color: C.amber,
    fontFace: FONT_B, margin: 0,
  });

  addFooter(s, 9);
  s.addNotes(
    "네 번째 소스인 Kaggle 데이터는 배치 데이터로 오백칠십만 행 곱하기 31 컬럼, 용량은 580 메가바이트입니다. " +
    "지연된 편이 전체의 38.8 퍼센트, 취소가 3.4 퍼센트, 평균 도착 지연이 6.2 분이고, 최대 지연은 무려 천구백칠십일 분, 즉 약 32 시간입니다. " +
    "특히 중요한 발견은 전체 지연의 39.6 퍼센트가 '전편 지연' 즉 cascade 또는 reactionary 딜레이에서 발생한다는 점입니다. " +
    "이 40 퍼센트라는 숫자가 뒤에 나올 Rotation features 의 도메인 근거가 되니 꼭 기억해 주시기 바랍니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 10 · 데이터 포맷 진화
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 04 · DATA FORMAT", "데이터 포맷의 진화", "From JSON to Avro — why the upgrade?");

  const fmts = [
    {
      name: "JSON", desc: "읽기 쉬움\nhuman-readable", size: "100 B",
      pros: ["사람 읽기 쉬움", "debug 편함"], cons: ["스키마 없음", "타입 없음", "크기 큼"],
      color: C.amber, x: 0.5,
    },
    {
      name: "CSV", desc: "가볍지만 단순\nlight but flat", size: "60 B",
      pros: ["가장 가벼움", "Excel 호환"], cons: ["타입 없음", "중첩 불가", "이스케이프 난해"],
      color: C.teal, x: 3.6,
    },
    {
      name: "Avro ★", desc: "스키마 강제\nschema-enforced", size: "35 B",
      pros: ["스키마 진화", "이진 압축", "타입 안전"], cons: ["사람 읽기 어려움"],
      color: C.skyBlue, x: 6.7,
    },
  ];

  fmts.forEach((f) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: f.x, y: 1.05, w: 2.8, h: 4.1, fill: { color: C.white }, line: { color: f.color, width: 2 }, rectRadius: 0.1,
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: f.x, y: 1.05, w: 2.8, h: 0.5, fill: { color: f.color }, line: { color: f.color },
    });
    s.addText(f.name, {
      x: f.x, y: 1.05, w: 2.8, h: 0.5, fontSize: 18, bold: true, color: C.white,
      fontFace: FONT_T, align: "center", valign: "middle", margin: 0,
    });
    s.addText(f.desc, {
      x: f.x + 0.15, y: 1.65, w: 2.5, h: 0.5, fontSize: 10, color: C.slate, fontFace: FONT_B,
      align: "center", margin: 0,
    });
    s.addText(`1 record ≈ ${f.size}`, {
      x: f.x + 0.15, y: 2.1, w: 2.5, h: 0.3, fontSize: 11, bold: true, color: f.color,
      fontFace: FONT_M, align: "center", margin: 0,
    });
    // pros
    s.addText("✅ 장점 (Pros)", {
      x: f.x + 0.15, y: 2.5, w: 2.5, h: 0.25, fontSize: 10, bold: true, color: C.green, fontFace: FONT_T, margin: 0,
    });
    f.pros.forEach((p, i) => {
      s.addText("· " + p, {
        x: f.x + 0.2, y: 2.78 + i * 0.22, w: 2.5, h: 0.22, fontSize: 9, color: C.slate,
        fontFace: FONT_B, margin: 0,
      });
    });
    // cons
    const consY = 2.78 + f.pros.length * 0.22 + 0.15;
    s.addText("❌ 단점 (Cons)", {
      x: f.x + 0.15, y: consY, w: 2.5, h: 0.25, fontSize: 10, bold: true, color: C.coral, fontFace: FONT_T, margin: 0,
    });
    f.cons.forEach((p, i) => {
      s.addText("· " + p, {
        x: f.x + 0.2, y: consY + 0.28 + i * 0.22, w: 2.5, h: 0.22, fontSize: 9, color: C.slate,
        fontFace: FONT_B, margin: 0,
      });
    });
  });

  addFooter(s, 10);
  s.addNotes(
    "똑같은 항공기 위치 한 건이라도 JSON 으로는 100 바이트, CSV 로는 60 바이트, Avro 로는 35 바이트에 담을 수 있습니다. " +
    "초당 수천 건이 흐르는 Kafka 환경에서는 이 차이가 하루 누적 수십 기가바이트의 차이를 만듭니다. " +
    "하지만 제가 Avro 를 선택한 가장 큰 이유는 크기보다 스키마 강제이고, 다음 슬라이드에서 자세히 설명드립니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 11 · Schema Registry 필요성
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 04 · DATA FORMAT", "왜 Schema Registry 인가?", "Why Schema Registry? — a real failure scenario");

  // Before
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 1.1, w: 4.3, h: 3.9, fill: { color: C.white }, line: { color: C.coral, width: 2 }, rectRadius: 0.1,
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.1, w: 4.3, h: 0.45, fill: { color: C.coral }, line: { color: C.coral },
  });
  s.addText("❌  BEFORE — 스키마 없이 (no schema)", {
    x: 0.5, y: 1.1, w: 4.3, h: 0.45, fontSize: 12, bold: true, color: C.white,
    fontFace: FONT_T, align: "center", valign: "middle", margin: 0,
  });
  s.addText([
    { text: "Producer 가 새 필드를 추가:\n", options: { bold: true, color: C.navy, fontSize: 10 } },
    { text: "{\n  \"icao24\": ...,\n  \"speed_kt\": 245,  ← 새 필드\n}\n\n", options: { fontFace: FONT_M, fontSize: 9, color: C.slate } },
    { text: "Consumer 가 기존 코드로 읽음:\n", options: { bold: true, color: C.navy, fontSize: 10 } },
    { text: "msg.velocity_ms   ← KeyError!\n💥 서비스 다운\n", options: { fontFace: FONT_M, fontSize: 9, color: C.coral } },
    { text: "\n디버깅: 어느 producer 가 언제 바꿨나?\n(Debug: who changed what when?)",
      options: { italic: true, color: C.mute, fontSize: 9 } },
  ], {
    x: 0.7, y: 1.7, w: 3.9, h: 3.2, fontFace: FONT_B, margin: 0,
  });

  // After
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 5.2, y: 1.1, w: 4.3, h: 3.9, fill: { color: C.white }, line: { color: C.green, width: 2 }, rectRadius: 0.1,
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: 1.1, w: 4.3, h: 0.45, fill: { color: C.green }, line: { color: C.green },
  });
  s.addText("✅  AFTER — Schema Registry (BACKWARD)", {
    x: 5.2, y: 1.1, w: 4.3, h: 0.45, fontSize: 12, bold: true, color: C.white,
    fontFace: FONT_T, align: "center", valign: "middle", margin: 0,
  });
  s.addText([
    { text: "Producer 가 호환 안되는 변경 시도:\n", options: { bold: true, color: C.navy, fontSize: 10 } },
    { text: "POST /subjects/flight-position\n  + rename field\n\n", options: { fontFace: FONT_M, fontSize: 9, color: C.slate } },
    { text: "Schema Registry 가 즉시 거부:\n", options: { bold: true, color: C.navy, fontSize: 10 } },
    { text: "409 Conflict: BACKWARD incompat.\n✅ 배포 전에 막힘\n\n", options: { fontFace: FONT_M, fontSize: 9, color: C.green } },
    { text: "호환되는 변경 (default 있는 필드 추가) 은 통과.\n",
      options: { color: C.slate, fontSize: 9 } },
    { text: "기존 consumer 는 default 값으로 안전하게 동작.",
      options: { italic: true, color: C.mute, fontSize: 9 } },
  ], {
    x: 5.4, y: 1.7, w: 3.9, h: 3.2, fontFace: FONT_B, margin: 0,
  });

  addFooter(s, 11);
  s.addNotes(
    "스키마가 없으면 producer 가 새 필드를 추가했을 때 기존 consumer 가 옛 필드명을 기대하고 있기 때문에 KeyError 를 던지며 서비스가 다운됩니다. " +
    "그리고 누가 언제 무엇을 바꿨는지 아무도 답할 수 없습니다. " +
    "Schema Registry 에 BACKWARD 호환 정책을 적용해 두면, 호환이 깨지는 변경은 배포 전에 409 Conflict 응답으로 거부됩니다. " +
    "호환되는 변경은 통과되고 기존 consumer 는 default 값으로 안전하게 동작합니다. " +
    "BACKWARD 호환은 새 consumer 가 옛 데이터도 읽을 수 있어야 한다는 뜻이고, 덕분에 장애 상황에서 이전 버전으로 롤백하는 것이 안전해집니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 12 · 전처리 5단계 개요
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 05 · PREPROCESSING", "전처리 6단계 파이프라인", "The 6-Step Preprocessing Pipeline");

  // 단계별 메타 — 이모지 제거, 단계 이니셜 텍스트로 대체 (PPT 호환성)
  const steps = [
    { n: 1, abbr: "CLN", ko: "정제 Clean",           sub: "결측·이상·중복",    color: C.coral },
    { n: 2, abbr: "NA",  ko: "결측값 Missing",       sub: "drop / impute / xgb", color: C.amber },
    { n: 3, abbr: "FE",  ko: "Feature Eng.",         sub: "시간·거리 분해",      color: C.teal },
    { n: 4, abbr: "ROT", ko: "Rotation Feats",       sub: "P1 · +335% R²",       color: C.skyBlue },
    { n: 5, abbr: "SPL", ko: "Split 분할",           sub: "TimeSeriesSplit",     color: C.purple },
    { n: 6, abbr: "ICE", ko: "Iceberg 저장",         sub: "Bronze/Silver/Gold",  color: C.green },
  ];

  steps.forEach((st, i) => {
    const x = 0.5 + i * 1.55;
    // 큰 컬러 원 (main bubble)
    s.addShape(pres.shapes.OVAL, {
      x: x + 0.15, y: 1.3, w: 1.2, h: 1.2, fill: { color: st.color }, line: { color: st.color },
    });
    // 원 내부에 큰 abbr 텍스트
    s.addText(st.abbr, {
      x: x + 0.15, y: 1.3, w: 1.2, h: 1.2, fontSize: 19, bold: true, color: C.white,
      fontFace: FONT_T, align: "center", valign: "middle", margin: 0,
      charSpacing: 1,
    });
    // 단계 번호 — 메인 원 내부 좌상단에 작은 배지로 (overlap 제거)
    s.addShape(pres.shapes.OVAL, {
      x: x + 0.05, y: 1.2, w: 0.42, h: 0.42, fill: { color: C.navy }, line: { color: C.white, width: 2 },
    });
    s.addText(String(st.n), {
      x: x + 0.05, y: 1.2, w: 0.42, h: 0.42, fontSize: 13, bold: true, color: C.white,
      fontFace: FONT_T, align: "center", valign: "middle", margin: 0,
    });
    // 라벨 (한/영 한 줄)
    s.addText(st.ko, {
      x: x - 0.1, y: 2.6, w: 1.7, h: 0.35, fontSize: 11, bold: true, color: C.navy,
      fontFace: FONT_T, align: "center", margin: 0,
    });
    s.addText(st.sub, {
      x: x - 0.1, y: 2.95, w: 1.7, h: 0.3, fontSize: 9, color: C.mute, italic: true,
      fontFace: FONT_B, align: "center", margin: 0,
    });
    // 단계 간 화살표 (원 사이 중앙 정확히)
    if (i < steps.length - 1) {
      s.addShape(pres.shapes.LINE, {
        x: x + 1.38, y: 1.9, w: 0.15, h: 0,
        line: { color: C.amber, width: 3, endArrowType: "triangle" },
      });
    }
  });

  // Input/Output 표시
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 3.7, w: 4.2, h: 1.3, fill: { color: C.ice }, line: { color: C.coral, width: 1.5 }, rectRadius: 0.08,
  });
  s.addText("📥  INPUT", {
    x: 0.7, y: 3.75, w: 4.0, h: 0.3, fontSize: 11, bold: true, color: C.coral, fontFace: FONT_T, margin: 0,
  });
  s.addText("Raw flights.csv  (5.7M rows · 31 cols)\n✘ 결측·이상치·중복 포함\n✘ 타입 불일치\n✘ 사용할 수 없음 that's why we preprocess", {
    x: 0.7, y: 4.0, w: 4.0, h: 1.0, fontSize: 10, color: C.slate, fontFace: FONT_B, margin: 0,
  });

  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 5.3, y: 3.7, w: 4.2, h: 1.3, fill: { color: C.ice }, line: { color: C.green, width: 1.5 }, rectRadius: 0.08,
  });
  s.addText("📤  OUTPUT", {
    x: 5.5, y: 3.75, w: 4.0, h: 0.3, fontSize: 11, bold: true, color: C.green, fontFace: FONT_T, margin: 0,
  });
  s.addText("train/val/test.parquet  (400k / 50k / 50k)\n✔ 25 numeric + 3 categorical = 28 features\n✔ 시간순 split (no leakage)\n✔ Model-ready", {
    x: 5.5, y: 4.0, w: 4.0, h: 1.0, fontSize: 10, color: C.slate, fontFace: FONT_B, margin: 0,
  });

  addFooter(s, 12);
  s.addNotes(
    "모든 ML 프로젝트는 결국 여섯 단계를 거칩니다. " +
    "Clean 으로 결측과 이상, 중복을 제거하고, Missing 으로 NaN 을 세 가지 전략으로 처리합니다. " +
    "그다음 Feature Engineering 으로 원본 값을 분해하고, Rotation Features 에서 도메인 지식을 주입해 R² 를 335 퍼센트 끌어올렸습니다. " +
    "Split 에서 TimeSeriesSplit 으로 시간순 분할을 하고, 마지막 Iceberg 에서 Bronze, Silver, Gold 계층에 저장합니다. " +
    "왼쪽의 오백칠십만 행 raw 데이터가 오른쪽의 40만, 5만, 5만 행 model-ready 학습 세트로 변환되는 것이 이 여섯 단계 안에서 일어납니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 13 · Step 1 · Raw → Clean
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 05 · STEP 1", "Raw → Clean · 실제 문제", "What does 'dirty data' look like?");

  // 원본 샘플 테이블 (문제 있는 행)
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 1.05, w: 8.9, h: 2.0, fill: { color: C.white }, line: { color: C.coral, width: 1.5 }, rectRadius: 0.08,
  });
  s.addText("🔍  실제 원본 데이터에서 발견한 문제 (real issues in the raw data)", {
    x: 0.7, y: 1.1, w: 8.6, h: 0.3, fontSize: 12, bold: true, color: C.coral, fontFace: FONT_T, margin: 0,
  });

  // Header row — WEATHER_DELAY (항상 null) 제거하고 문제유형 컬럼 추가
  const cols = ["FL_DATE", "AIRLINE", "ORIGIN", "DEP_DELAY", "DISTANCE", "문제 유형 / Issue"];
  const colX = [0.7, 2.0, 3.1, 4.1, 5.2, 6.3];
  const colW = [1.3, 1.1, 1.0, 1.0, 1.0, 3.0];
  cols.forEach((c, i) => {
    s.addShape(pres.shapes.RECTANGLE, {
      x: colX[i], y: 1.5, w: colW[i], h: 0.3, fill: { color: C.navy }, line: { color: C.navy },
    });
    s.addText(c, {
      x: colX[i], y: 1.5, w: colW[i], h: 0.3, fontSize: 9, bold: true, color: C.white,
      fontFace: i === 5 ? FONT_T : FONT_M, align: "center", valign: "middle", margin: 0,
    });
  });

  // 6-tuple: FL_DATE, AIRLINE, ORIGIN, DEP_DELAY, DISTANCE, ISSUE_LABEL
  const rows = [
    ["2015-01-05", "UA",  "SFO",  "15",     "2586",  "OK"],
    ["2015-01-05", "UA",  "SFO",  "15",     "2586",  "⚠ 중복 duplicate"],
    ["2015-01-06", "",    "LAX",  "null",   "325",   "⚠ 결측 missing"],
    ["2015-01-07", "DL",  "JFK",  "-9999",  "2475",  "⚠ 센서오류 sentinel"],
    ["2015-01-08", "AA",  "ORD",  "48",     "-1",    "⚠ 거리 음수 invalid"],
    ["2015-01-09", "WN",  "BWI",  "8",      "412",   "✓ OK"],
  ];
  rows.forEach((r, ri) => {
    const y = 1.82 + ri * 0.22;
    const rowColor = r[5].startsWith("⚠") ? "FFF0F0" : C.white;
    for (let i = 0; i < 5; i++) {
      // 데이터 셀 0-4 (FL_DATE ~ DISTANCE)
      s.addShape(pres.shapes.RECTANGLE, {
        x: colX[i], y, w: colW[i], h: 0.22, fill: { color: rowColor }, line: { color: "DDDDDD", width: 0.5 },
      });
      const cellColor = (r[i] === "null" || r[i] === "" || r[i] === "-9999" || r[i] === "-1") ? C.coral : C.slate;
      s.addText(r[i] === "" ? "—" : r[i], {
        x: colX[i], y, w: colW[i], h: 0.22, fontSize: 8.5, color: cellColor,
        fontFace: FONT_M, align: "center", valign: "middle", margin: 0,
        bold: (cellColor === C.coral),
      });
    }
    // 문제유형 셀 (컬럼 5) — 유일한 라벨 위치
    s.addShape(pres.shapes.RECTANGLE, {
      x: colX[5], y, w: colW[5], h: 0.22, fill: { color: rowColor }, line: { color: "DDDDDD", width: 0.5 },
    });
    const labelColor = r[5].startsWith("⚠") ? C.coral : C.green;
    s.addText(r[5], {
      x: colX[5] + 0.1, y, w: colW[5] - 0.1, h: 0.22, fontSize: 8.5, color: labelColor,
      fontFace: FONT_B, bold: true, align: "left", valign: "middle", margin: 0,
    });
  });

  // 해결법 4개
  s.addText("해결 전략 (Cleaning strategies)", {
    x: 0.5, y: 3.25, w: 9, h: 0.3, fontSize: 13, bold: true, color: C.navy, fontFace: FONT_T, margin: 0,
  });
  const fixes = [
    { ico: "🗑", ko: "중복 제거",   en: "drop_duplicates()",        color: C.coral },
    { ico: "🔢", ko: "결측값 처리", en: "fillna / imputer / xgb",   color: C.amber },
    { ico: "🚫", ko: "Sentinel 교체", en: "-9999 → NaN",             color: C.teal },
    { ico: "📏", ko: "범위 검증",    en: "distance > 0 필터",        color: C.skyBlue },
  ];
  fixes.forEach((f, i) => {
    const x = 0.5 + i * 2.28;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 3.6, w: 2.15, h: 1.45, fill: { color: C.white }, line: { color: f.color, width: 1.5 }, rectRadius: 0.08,
    });
    s.addText(f.ico, {
      x, y: 3.7, w: 2.15, h: 0.55, fontSize: 28, align: "center", valign: "middle", fontFace: FONT_T, margin: 0,
    });
    s.addText(f.ko, {
      x, y: 4.3, w: 2.15, h: 0.35, fontSize: 12, bold: true, color: C.navy,
      fontFace: FONT_T, align: "center", margin: 0,
    });
    s.addText(f.en, {
      x, y: 4.65, w: 2.15, h: 0.3, fontSize: 9, italic: true, color: f.color,
      fontFace: FONT_M, align: "center", margin: 0,
    });
  });

  addFooter(s, 13);
  s.addNotes(
    "진짜 원본 데이터가 얼마나 지저분한지 보여드립니다. " +
    "똑같은 레코드가 두 번 등장하는 중복이 있고, AIRLINE 필드가 비어 있고 DEP_DELAY 가 null 인 결측이 있으며, " +
    "DEP_DELAY 값이 마이너스 구천구백구십구인 경우는 실제 지연이 아니라 센서 오류 마커인 sentinel value 입니다. " +
    "DISTANCE 가 마이너스 일인 경우는 거리가 음수일 수 없으니 범위 오류로 처리해야 합니다. " +
    "중복은 drop_duplicates 로 제거하고, 결측은 세 전략으로 처리하며, sentinel 은 NaN 으로 치환하고, 범위는 필터로 잡아냅니다. " +
    "이 과정을 건너뛰고 바로 모델에 넣으면 GIGO, 즉 쓰레기를 넣으면 쓰레기가 나오는 현상이 발생합니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 14 · Step 2 · 결측값 처리 3전략
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 05 · STEP 2", "결측값 (Missing Value) 3 전략", "Three Strategies for Missing Values");

  const strats = [
    {
      name: "① Drop",
      ko: "그냥 삭제",
      en: "drop NaN rows",
      code: "df.dropna()",
      pros: "가장 간단\nsimple",
      cons: "데이터 대량 손실\ndata loss",
      color: C.coral,
      x: 0.5,
    },
    {
      name: "② Impute",
      ko: "평균·중간값 대체",
      en: "fill with mean/median",
      code: "SimpleImputer(mean)",
      pros: "데이터 유지\nkeep rows",
      cons: "분산 왜곡\nbias variance",
      color: C.amber,
      x: 3.5,
    },
    {
      name: "③ XGBoost ★",
      ko: "자동 처리",
      en: "native NaN handling",
      code: "XGBoost uses NaN as a split direction",
      pros: "최적 분할 자동\noptimal branch",
      cons: "다른 모델 X\nmodel-specific",
      color: C.green,
      x: 6.5,
    },
  ];

  strats.forEach((st) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: st.x, y: 1.1, w: 2.9, h: 3.95, fill: { color: C.white }, line: { color: st.color, width: 2 }, rectRadius: 0.1,
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: st.x, y: 1.1, w: 2.9, h: 0.45, fill: { color: st.color }, line: { color: st.color },
    });
    s.addText(st.name, {
      x: st.x, y: 1.1, w: 2.9, h: 0.45, fontSize: 14, bold: true, color: C.white,
      fontFace: FONT_T, align: "center", valign: "middle", margin: 0,
    });
    s.addText(st.ko, {
      x: st.x + 0.15, y: 1.65, w: 2.6, h: 0.35, fontSize: 14, bold: true, color: C.navy,
      fontFace: FONT_T, align: "center", margin: 0,
    });
    s.addText(st.en, {
      x: st.x + 0.15, y: 2.0, w: 2.6, h: 0.3, fontSize: 10, italic: true, color: C.mute,
      fontFace: FONT_B, align: "center", margin: 0,
    });
    // code
    s.addShape(pres.shapes.RECTANGLE, {
      x: st.x + 0.15, y: 2.4, w: 2.6, h: 0.6, fill: { color: C.navy }, line: { color: C.navy },
    });
    s.addText(st.code, {
      x: st.x + 0.2, y: 2.45, w: 2.5, h: 0.5, fontSize: 9.5, color: C.amber,
      fontFace: FONT_M, align: "center", valign: "middle", margin: 0, bold: true,
    });
    // pros
    s.addText("✅ " + st.pros, {
      x: st.x + 0.15, y: 3.15, w: 2.6, h: 0.55, fontSize: 10, color: C.green, bold: true,
      fontFace: FONT_B, align: "center", margin: 0,
    });
    // cons
    s.addText("❌ " + st.cons, {
      x: st.x + 0.15, y: 3.8, w: 2.6, h: 0.55, fontSize: 10, color: C.coral, bold: true,
      fontFace: FONT_B, align: "center", margin: 0,
    });
  });

  // 제가 선택한 것
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 5.1, w: 8.9, h: 0, fill: { color: C.navy }, line: { color: C.navy, width: 0 },
  });
  s.addText([
    { text: "💡 제 프로젝트: ", options: { bold: true, color: C.amber, fontSize: 11 } },
    { text: "전처리 파이프라인에 SimpleImputer 를 넣고, 최종 모델은 XGBoost 라 native handling 도 동시에 작동", options: { color: C.white, fontSize: 10 } },
  ], {
    x: 0.5, y: 4.68, w: 8.9, h: 0.35, fill: { color: C.navy }, fontFace: FONT_B, margin: 0,
    valign: "middle",
  });

  addFooter(s, 14);
  s.addNotes(
    "결측값을 처리하는 방법에는 세 가지 전략이 있습니다. " +
    "첫 번째 Drop 은 그냥 버리는 방식이고, 두 번째 Impute 는 평균이나 중간값으로 채우는 방식이며, " +
    "세 번째 XGBoost Native 는 결측값을 분할 방향 자체로 학습하는 방식입니다. " +
    "XGBoost 가 인기 있는 이유가 여기 있습니다. 로지스틱 회귀나 kNN 같은 다른 모델은 NaN 이 하나라도 있으면 아예 학습조차 안 됩니다. " +
    "저는 sklearn Pipeline 에 SimpleImputer 를 넣고 최종 estimator 로 XGBoost 를 두는 이중 안전망 구조를 쓰고 있습니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 15 · Step 3 · Feature Engineering 기초
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 05 · STEP 3", "Feature Engineering 기초", "Why strings can't be features");

  // Before/After 분해 예시
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 1.05, w: 4.2, h: 1.85, fill: { color: C.white }, line: { color: C.coral, width: 2 }, rectRadius: 0.08,
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.05, w: 4.2, h: 0.4, fill: { color: C.coral }, line: { color: C.coral },
  });
  s.addText("❌ Before — 모델이 못 읽음", {
    x: 0.5, y: 1.05, w: 4.2, h: 0.4, fontSize: 12, bold: true, color: C.white,
    fontFace: FONT_T, align: "center", valign: "middle", margin: 0,
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 1.6, w: 3.8, h: 1.1, fill: { color: C.ice }, line: { color: C.ice },
  });
  s.addText("\"2026-04-19 14:30:00\"", {
    x: 0.7, y: 1.85, w: 3.8, h: 0.45, fontSize: 18, bold: true, color: C.navy,
    fontFace: FONT_M, align: "center", valign: "middle", margin: 0,
  });
  s.addText("datetime string\n모델은 문자열을 이해하지 못함", {
    x: 0.7, y: 2.3, w: 3.8, h: 0.35, fontSize: 9, italic: true, color: C.mute,
    fontFace: FONT_B, align: "center", margin: 0,
  });

  // Arrow — 양쪽 박스 사이 중앙, 텍스트 래핑 방지 위해 폭 확보
  s.addShape(pres.shapes.LINE, {
    x: 4.72, y: 1.95, w: 0.56, h: 0,
    line: { color: C.amber, width: 4, endArrowType: "triangle" },
  });
  // "분해 / decompose" — 화살표 아래 가로로 짧게
  s.addText("분해 decompose", {
    x: 4.5, y: 2.15, w: 1.0, h: 0.3, fontSize: 10, bold: true, color: C.amber,
    fontFace: FONT_T, align: "center", valign: "middle", margin: 0,
  });

  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 5.3, y: 1.05, w: 4.2, h: 1.85, fill: { color: C.white }, line: { color: C.green, width: 2 }, rectRadius: 0.08,
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.3, y: 1.05, w: 4.2, h: 0.4, fill: { color: C.green }, line: { color: C.green },
  });
  s.addText("✅ After — 6개 숫자 Feature", {
    x: 5.3, y: 1.05, w: 4.2, h: 0.4, fontSize: 12, bold: true, color: C.white,
    fontFace: FONT_T, align: "center", valign: "middle", margin: 0,
  });

  const feats = [
    ["hour", "14"], ["minute", "30"], ["dayofweek", "6"],
    ["month", "4"], ["dayofyear", "109"], ["is_weekend", "1"],
  ];
  feats.forEach((f, i) => {
    const col = i % 3;
    const row = Math.floor(i / 3);
    const x = 5.45 + col * 1.35;
    const y = 1.6 + row * 0.55;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y, w: 1.25, h: 0.47, fill: { color: C.ice }, line: { color: C.green, width: 0.8 }, rectRadius: 0.06,
    });
    s.addText(f[0], {
      x, y: y + 0.02, w: 1.25, h: 0.22, fontSize: 9, color: C.green, bold: true,
      fontFace: FONT_M, align: "center", margin: 0,
    });
    s.addText(f[1], {
      x, y: y + 0.21, w: 1.25, h: 0.24, fontSize: 14, bold: true, color: C.navy,
      fontFace: FONT_M, align: "center", margin: 0,
    });
  });

  // 왜 중요한가
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 3.15, w: 8.9, h: 1.9, fill: { color: C.navy }, line: { color: C.navy }, rectRadius: 0.1,
  });
  s.addText("🔑  왜 이렇게 분해하나? (Why decompose?)", {
    x: 0.7, y: 3.25, w: 8.6, h: 0.35, fontSize: 13, bold: true, color: C.amber, fontFace: FONT_T, margin: 0,
  });
  s.addText([
    { text: "• 주중 ≠ 주말: ", options: { bold: true, color: C.white, fontSize: 11 } },
    { text: "평일 18시 혼잡도 ≠ 토요일 18시 혼잡도\n", options: { color: C.ice, fontSize: 10 } },
    { text: "  weekday 18:00 congestion ≠ weekend 18:00\n", options: { italic: true, color: C.mute, fontSize: 9 } },
    { text: "• 월별 패턴: ", options: { bold: true, color: C.white, fontSize: 11 } },
    { text: "여름 휴가철 7·8월 지연률 ↑, 봄 4·5월 ↓\n", options: { color: C.ice, fontSize: 10 } },
    { text: "  seasonal pattern (summer peak, spring calm)\n", options: { italic: true, color: C.mute, fontSize: 9 } },
    { text: "• 시간대 패턴: ", options: { bold: true, color: C.white, fontSize: 11 } },
    { text: "오전 06시 출발은 거의 정시, 저녁 18시는 지연 누적", options: { color: C.ice, fontSize: 10 } },
  ], {
    x: 0.7, y: 3.65, w: 8.6, h: 1.35, fontFace: FONT_B, margin: 0,
  });

  addFooter(s, 15);
  s.addNotes(
    "모델은 문자열을 읽지 못하고 오직 숫자만 이해할 수 있습니다. " +
    "2026-04-19 14:30:00 같은 datetime 문자열을 그대로 넣으면 모델이 아무 정보도 얻지 못합니다. " +
    "hour 14, minute 30, dayofweek 6, month 4, dayofyear 109, is_weekend 1 처럼 여섯 개의 숫자 피처로 분해해야 모델이 주중과 주말의 차이, 월별 패턴, 시간대 패턴을 각각 독립적으로 볼 수 있습니다. " +
    "평일 18 시 혼잡도와 토요일 18 시 혼잡도가 다르고, 7 월과 8 월은 지연이 많으며, 오전 6 시는 정시인 반면 저녁 18 시는 지연이 누적됩니다. " +
    "이것이 Feature Engineering 의 출발점입니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 16 · Step 4 · Rotation Features (+335% R²)
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 05 · STEP 4 ★", "Rotation Features — 실제 사례", "Real case: +335% R² from 5 features");

  // 큰 숫자 임팩트
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 1.05, w: 4.3, h: 1.7, fill: { color: C.navy }, line: { color: C.navy }, rectRadius: 0.1,
  });
  s.addText("Test R²", {
    x: 0.5, y: 1.15, w: 4.3, h: 0.3, fontSize: 10, color: C.ice, fontFace: FONT_T, align: "center", margin: 0,
  });
  s.addText([
    { text: "0.10", options: { color: C.coral, fontSize: 30, bold: true } },
    { text: "   →   ", options: { color: C.white, fontSize: 26 } },
    { text: "0.43", options: { color: C.green, fontSize: 30, bold: true } },
  ], {
    x: 0.5, y: 1.5, w: 4.3, h: 0.6, fontFace: FONT_T, align: "center", valign: "middle", margin: 0,
  });
  s.addText("+335% 향상 · same XGBoost · 5 features 추가만", {
    x: 0.5, y: 2.12, w: 4.3, h: 0.25, fontSize: 10, bold: true, color: C.amber,
    fontFace: FONT_B, align: "center", margin: 0,
  });
  s.addText("P1 sprint · 2026-04-14", {
    x: 0.5, y: 2.42, w: 4.3, h: 0.25, fontSize: 9, italic: true, color: C.mute,
    fontFace: FONT_B, align: "center", margin: 0,
  });

  // 아이디어
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 4.9, y: 1.05, w: 4.5, h: 1.7, fill: { color: C.white }, line: { color: C.skyBlue, width: 2 }, rectRadius: 0.1,
  });
  s.addText("💡  핵심 아이디어 (Key idea)", {
    x: 5.0, y: 1.15, w: 4.3, h: 0.3, fontSize: 12, bold: true, color: C.skyBlue, fontFace: FONT_T, margin: 0,
  });
  s.addText([
    { text: "같은 비행기가 하루에 3-5번 뜬다.\n", options: { color: C.navy, fontSize: 11, bold: true } },
    { text: "Same aircraft flies 3-5 legs per day.\n", options: { color: C.mute, fontSize: 9, italic: true } },
    { text: "\n지연은 ", options: { color: C.slate, fontSize: 10 } },
    { text: "누적 ", options: { color: C.coral, fontSize: 10, bold: true } },
    { text: "됨 (reactionary = 45%).\n", options: { color: C.slate, fontSize: 10 } },
    { text: "Delay propagates (reactionary = 45% · EUROCONTROL).\n", options: { italic: true, color: C.mute, fontSize: 9 } },
  ], {
    x: 5.0, y: 1.45, w: 4.3, h: 1.3, fontFace: FONT_B, margin: 0,
  });

  // Rotation chain visualization (plane's day)
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 2.95, w: 8.9, h: 1.4, fill: { color: C.white }, line: { color: C.slate, width: 1 }, rectRadius: 0.08,
  });
  s.addText("🛩  항공기 HL8281 의 하루 (a day of tail number HL8281)", {
    x: 0.7, y: 3.0, w: 8.6, h: 0.3, fontSize: 11, bold: true, color: C.navy, fontFace: FONT_T, margin: 0,
  });

  const legs = [
    { time: "06:00", route: "ICN→CJU", delay: "+2", color: C.green },
    { time: "09:00", route: "CJU→ICN", delay: "+5", color: C.green },
    { time: "12:00", route: "ICN→CJU", delay: "+12", color: C.amber },
    { time: "15:00", route: "CJU→ICN", delay: "+24", color: C.coral },
    { time: "18:00", route: "ICN→CJU", delay: "+45?", color: C.coral },
  ];
  legs.forEach((l, i) => {
    const x = 0.7 + i * 1.76;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 3.42, w: 1.6, h: 0.85, fill: { color: l.color }, line: { color: l.color }, rectRadius: 0.05,
    });
    s.addText(l.time, {
      x, y: 3.45, w: 1.6, h: 0.25, fontSize: 10, bold: true, color: C.white,
      fontFace: FONT_M, align: "center", margin: 0,
    });
    s.addText(l.route, {
      x, y: 3.7, w: 1.6, h: 0.25, fontSize: 10, color: C.white, fontFace: FONT_M, align: "center", margin: 0,
    });
    s.addText(l.delay + " 분", {
      x, y: 3.95, w: 1.6, h: 0.25, fontSize: 11, bold: true, color: C.white, fontFace: FONT_T,
      align: "center", margin: 0,
    });
    if (i < legs.length - 1) {
      s.addText("→", {
        x: x + 1.6, y: 3.52, w: 0.2, h: 0.6, fontSize: 18, bold: true, color: C.slate,
        align: "center", valign: "middle", margin: 0,
      });
    }
  });

  // 5개 feature
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 4.45, w: 8.9, h: 0.6, fill: { color: C.ice }, line: { color: C.skyBlue, width: 1 }, rectRadius: 0.05,
  });
  s.addText([
    { text: "📌 추가한 5개 features: ", options: { bold: true, color: C.skyBlue, fontSize: 10 } },
    { text: "rotation_depth · prev_leg_arr_delay_min · scheduled_turnaround_min · actual_turnaround_min · is_first_leg_of_day",
      options: { color: C.navy, fontSize: 9.5, fontFace: FONT_M } },
  ], {
    x: 0.7, y: 4.5, w: 8.6, h: 0.5, fontFace: FONT_B, margin: 0, valign: "middle",
  });

  addFooter(s, 16);
  s.addNotes(
    "이 슬라이드는 이번 발표에서 가장 중요한 슬라이드입니다. " +
    "Test R² 가 0.10 에서 0.43 으로 335 퍼센트 상승했는데, 같은 XGBoost 모델에 피처 다섯 개만 추가했을 뿐입니다. " +
    "핵심 아이디어는 같은 비행기가 하루에 세 번에서 다섯 번 뜨는데, 지연이 눈덩이처럼 누적된다는 점이었습니다. " +
    "예를 들어 HL8281 편은 06 시에는 2 분 지연, 09 시 5 분, 12 시 12 분, 15 시 24 분, 18 시에는 45 분까지 쌓입니다. " +
    "EUROCONTROL 연구에 따르면 전체 지연의 45 퍼센트가 이런 reactionary 딜레이입니다. " +
    "rotation_depth, prev_leg_arr_delay_min, scheduled_turnaround_min, actual_turnaround_min, is_first_leg_of_day 다섯 개 피처만으로 R² 가 3.35 배가 됐습니다. " +
    "교훈은 명확합니다. 모델을 키우는 것보다 도메인 지식을 피처로 만드는 것이 훨씬 효과적입니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 17 · Step 5 · Train/Test Split (중요!)
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 05 · STEP 5", "Train/Test Split — 흔한 실수", "The most common mistake in time-series ML");

  // WRONG
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 1.05, w: 4.3, h: 3.95, fill: { color: C.white }, line: { color: C.coral, width: 2 }, rectRadius: 0.1,
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.05, w: 4.3, h: 0.45, fill: { color: C.coral }, line: { color: C.coral },
  });
  s.addText("❌  WRONG — shuffle=True", {
    x: 0.5, y: 1.05, w: 4.3, h: 0.45, fontSize: 13, bold: true, color: C.white,
    fontFace: FONT_T, align: "center", valign: "middle", margin: 0,
  });
  s.addText("train_test_split(shuffle=True)", {
    x: 0.6, y: 1.6, w: 4.1, h: 0.35, fontSize: 11, color: C.coral, fontFace: FONT_M, bold: true,
    align: "center", margin: 0,
  });

  // Visual: colored timeline
  s.addText("Timeline  →", {
    x: 0.6, y: 2.0, w: 4.1, h: 0.25, fontSize: 9.5, italic: true, color: C.slate, fontFace: FONT_B, margin: 0,
  });
  // shuffled: TR TE TR TE TR TE ...
  const wrong = ["TR","TE","TR","TR","TE","TR","TE","TR","TR","TE"];
  wrong.forEach((t, i) => {
    const x = 0.6 + i * 0.41;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 2.3, w: 0.4, h: 0.3, fill: { color: t === "TE" ? C.coral : C.skyBlue }, line: { color: C.white, width: 0.5 },
    });
    s.addText(t, {
      x, y: 2.3, w: 0.4, h: 0.3, fontSize: 8, bold: true, color: C.white,
      fontFace: FONT_M, align: "center", valign: "middle", margin: 0,
    });
  });
  s.addText("💥  미래가 과거 훈련에 섞여 들어감\n    Future leaks into past training", {
    x: 0.6, y: 2.7, w: 4.1, h: 0.6, fontSize: 10, color: C.coral, bold: true, fontFace: FONT_B, margin: 0,
  });
  s.addText([
    { text: "결과: ", options: { bold: true, color: C.navy, fontSize: 10 } },
    { text: "CV 표준편차 ±0.30\n", options: { color: C.slate, fontSize: 10 } },
    { text: "(비정상적으로 작음 · 낙관적 편향)\n", options: { italic: true, color: C.mute, fontSize: 9 } },
    { text: "Result: CV std ±0.30 (artificially small)", options: { italic: true, color: C.mute, fontSize: 9 } },
  ], {
    x: 0.6, y: 3.4, w: 4.1, h: 1.4, fontFace: FONT_B, margin: 0,
  });

  // RIGHT
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 5.2, y: 1.05, w: 4.3, h: 3.95, fill: { color: C.white }, line: { color: C.green, width: 2 }, rectRadius: 0.1,
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: 1.05, w: 4.3, h: 0.45, fill: { color: C.green }, line: { color: C.green },
  });
  s.addText("✅  RIGHT — TimeSeriesSplit", {
    x: 5.2, y: 1.05, w: 4.3, h: 0.45, fontSize: 13, bold: true, color: C.white,
    fontFace: FONT_T, align: "center", valign: "middle", margin: 0,
  });
  s.addText("TimeSeriesSplit(n_splits=5)", {
    x: 5.3, y: 1.6, w: 4.1, h: 0.35, fontSize: 11, color: C.green, fontFace: FONT_M, bold: true,
    align: "center", margin: 0,
  });

  s.addText("Timeline  →", {
    x: 5.3, y: 2.0, w: 4.1, h: 0.25, fontSize: 9.5, italic: true, color: C.slate, fontFace: FONT_B, margin: 0,
  });
  const right = ["TR","TR","TR","TR","TR","TR","TR","TE","TE","TE"];
  right.forEach((t, i) => {
    const x = 5.3 + i * 0.41;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 2.3, w: 0.4, h: 0.3, fill: { color: t === "TE" ? C.coral : C.skyBlue }, line: { color: C.white, width: 0.5 },
    });
    s.addText(t, {
      x, y: 2.3, w: 0.4, h: 0.3, fontSize: 8, bold: true, color: C.white,
      fontFace: FONT_M, align: "center", valign: "middle", margin: 0,
    });
  });
  s.addText("✔  과거로만 학습, 미래로만 평가\n    Train on past, evaluate on future", {
    x: 5.3, y: 2.7, w: 4.1, h: 0.6, fontSize: 10, color: C.green, bold: true, fontFace: FONT_B, margin: 0,
  });
  s.addText([
    { text: "결과: ", options: { bold: true, color: C.navy, fontSize: 10 } },
    { text: "CV 표준편차 ±6.14\n", options: { color: C.slate, fontSize: 10 } },
    { text: "(정직한 수치 · 시간대별 변동성 반영)\n", options: { italic: true, color: C.mute, fontSize: 9 } },
    { text: "Result: CV std ±6.14 (honest, reflects temporal variance)",
      options: { italic: true, color: C.mute, fontSize: 9 } },
  ], {
    x: 5.3, y: 3.4, w: 4.1, h: 1.4, fontFace: FONT_B, margin: 0,
  });

  addFooter(s, 17);
  s.addNotes(
    "두 번째로 중요한 교훈이자 초심자가 가장 많이 범하는 치명적인 실수입니다. " +
    "sklearn 의 train_test_split 은 기본값이 shuffle True 라서 시간 축을 무시하고 무작위로 섞어 나눕니다. " +
    "그러면 미래가 과거 훈련에 섞여 들어가는 temporal leakage 가 발생하고, CV 표준편차가 플러스마이너스 0.30 으로 비정상적으로 작아 보이는 낙관적 편향이 생깁니다. " +
    "TimeSeriesSplit 의 walk-forward 방식을 쓰면 과거로만 학습하고 미래로만 평가하게 됩니다. " +
    "CV 표준편차가 플러스마이너스 6.14 로 20 배 증가하지만, 이것이 정직한 수치이고 시간대별 성능 변동성을 드러냅니다. " +
    "저는 이 원칙을 ADR-004 에 명시하고 파이프라인 전체를 수정했습니다. 여러분 코드에 shuffle True 가 시계열 데이터에 쓰이고 있다면 지금 당장 고치시기 바랍니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 18 · Step 6 · Iceberg Medallion
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 05 · STEP 6", "Iceberg Medallion 아키텍처", "Bronze / Silver / Gold — data lake pattern");

  const layers = [
    {
      name: "Bronze  🥉", ko: "원본 그대로", en: "raw, as-ingested",
      tables: "flight_position_raw\nweather_event_raw\nnotam_raw\natfm_restriction_raw",
      color: "8D6E63", x: 0.5,
    },
    {
      name: "Silver  🥈", ko: "정제 + 조인", en: "cleaned + joined",
      tables: "flight_features\naircraft_phase\nairport_context",
      color: "9E9E9E", x: 3.5,
    },
    {
      name: "Gold  🥇", ko: "모델 소비용 + 감사", en: "model-ready + audit",
      tables: "delay_train_split\ninference_log\nanomaly_decisions",
      color: "FFB300", x: 6.5,
    },
  ];

  layers.forEach((l, i) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: l.x, y: 1.1, w: 2.9, h: 3.0, fill: { color: C.white }, line: { color: l.color, width: 2 }, rectRadius: 0.1,
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: l.x, y: 1.1, w: 2.9, h: 0.5, fill: { color: l.color }, line: { color: l.color },
    });
    s.addText(l.name, {
      x: l.x, y: 1.1, w: 2.9, h: 0.5, fontSize: 16, bold: true, color: C.white,
      fontFace: FONT_T, align: "center", valign: "middle", margin: 0,
    });
    s.addText(l.ko, {
      x: l.x + 0.1, y: 1.7, w: 2.7, h: 0.35, fontSize: 13, bold: true, color: C.navy,
      fontFace: FONT_T, align: "center", margin: 0,
    });
    s.addText(l.en, {
      x: l.x + 0.1, y: 2.03, w: 2.7, h: 0.28, fontSize: 10, italic: true, color: C.mute,
      fontFace: FONT_B, align: "center", margin: 0,
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: l.x + 0.15, y: 2.42, w: 2.6, h: 1.55, fill: { color: C.cream }, line: { color: l.color, width: 0.5 },
    });
    s.addText(l.tables, {
      x: l.x + 0.25, y: 2.5, w: 2.4, h: 1.4, fontSize: 10, color: C.slate,
      fontFace: FONT_M, margin: 0, valign: "top",
    });
    if (i < layers.length - 1) {
      s.addText("→", {
        x: l.x + 2.9, y: 1.1, w: 0.3, h: 3.0, fontSize: 24, bold: true, color: C.amber,
        align: "center", valign: "middle", margin: 0,
      });
    }
  });

  // 왜 3 layer?
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 4.2, w: 8.9, h: 0.85, fill: { color: C.navy }, line: { color: C.navy }, rectRadius: 0.08,
  });
  s.addText([
    { text: "🔑 왜 3 계층? ", options: { bold: true, color: C.amber, fontSize: 11 } },
    { text: "ACID + schema evolution + time travel · 사고 시 '어디에서 틀어졌나' 추적 가능\n", options: { color: C.white, fontSize: 10 } },
    { text: "Why 3 layers? ", options: { bold: true, color: C.amber, fontSize: 10, italic: true } },
    { text: "Full reproducibility — ACID transactions + schema evolution + time-travel for incident forensics.",
      options: { color: C.ice, fontSize: 9, italic: true } },
  ], {
    x: 0.7, y: 4.3, w: 8.6, h: 0.7, fontFace: FONT_B, margin: 0, valign: "middle",
  });

  addFooter(s, 18);
  s.addNotes(
    "전처리의 마지막 단계는 저장인데, 그냥 CSV 에 저장하면 안 됩니다. " +
    "Apache Iceberg 의 Medallion 아키텍처를 Bronze, Silver, Gold 세 계층으로 나눠 쓰고 있습니다. " +
    "Bronze 는 원본 그대로 저장해서 재처리 기준점이 되고, Silver 는 정제와 조인이 끝난 flight_features 같은 통합 테이블이며, " +
    "Gold 는 모델이 직접 소비하는 inference_log 나 anomaly_decisions 같은 감사용 테이블입니다. " +
    "세 계층을 쓰는 이유는 ACID 트랜잭션으로 일관성을 유지하고, 스키마 진화를 지원하며, " +
    "Time travel 로 '3 일 전 테이블 상태가 어땠지' 같은 사고 조사용 쿼리가 가능하기 때문입니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 19 · 이 데이터로 만들 수 있는 프로젝트들
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 06 · APPLICATIONS", "이 데이터로 만들 수 있는 것들", "What can you build with aviation data?");

  const projs = [
    { icon: "⏱", ko: "지연 예측",         en: "Delay prediction",       color: C.skyBlue, ours: true },
    { icon: "💰", ko: "항공권 가격 예측",  en: "Ticket price forecast",  color: C.amber },
    { icon: "🏢", ko: "공항 혼잡도 예측",  en: "Airport congestion",     color: C.teal },
    { icon: "⛽", ko: "연료 소비 최적화",  en: "Fuel efficiency",        color: C.green },
    { icon: "🗺", ko: "운항 경로 최적화",  en: "Route optimization",     color: C.purple },
    { icon: "🌪", ko: "기상 영향 분석",    en: "Weather impact study",   color: C.orange },
    { icon: "⚠", ko: "이상 탐지",          en: "Anomaly detection",     color: C.coral, ours: true },
    { icon: "👥", ko: "승객 수요 예측",    en: "Demand forecasting",     color: C.slate },
  ];

  projs.forEach((p, i) => {
    const col = i % 4;
    const row = Math.floor(i / 4);
    const x = 0.5 + col * 2.25;
    const y = 1.1 + row * 1.9;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y, w: 2.1, h: 1.75, fill: { color: C.white },
      line: { color: p.color, width: p.ours ? 3 : 1.2 },
      rectRadius: 0.1,
    });
    // Badge for ours
    if (p.ours) {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: x + 1.35, y: y + 0.05, w: 0.7, h: 0.3, fill: { color: p.color }, line: { color: p.color }, rectRadius: 0.15,
      });
      s.addText("OURS", {
        x: x + 1.35, y: y + 0.05, w: 0.7, h: 0.3, fontSize: 8.5, bold: true, color: C.white,
        fontFace: FONT_T, align: "center", valign: "middle", margin: 0,
      });
    }
    s.addText(p.icon, {
      x, y: y + 0.2, w: 2.1, h: 0.7, fontSize: 38, align: "center", valign: "middle",
      fontFace: FONT_T, margin: 0,
    });
    s.addText(p.ko, {
      x, y: y + 0.95, w: 2.1, h: 0.35, fontSize: 12, bold: true, color: C.navy,
      fontFace: FONT_T, align: "center", margin: 0,
    });
    s.addText(p.en, {
      x, y: y + 1.3, w: 2.1, h: 0.3, fontSize: 9.5, italic: true, color: p.color,
      fontFace: FONT_B, align: "center", margin: 0,
    });
  });

  addFooter(s, 19);
  s.addNotes(
    "같은 데이터 셋으로 만들 수 있는 프로젝트가 최소 여덟 가지입니다. " +
    "지연 예측, 항공권 가격 예측, 공항 혼잡도 예측, 연료 소비 최적화, 운항 경로 최적화, 기상 영향 분석, 이상 탐지, 승객 수요 예측이 모두 가능합니다. " +
    "같은 데이터이지만 다른 질문, 다른 프로젝트가 만들어집니다. 여러분이 선택한 질문이 곧 여러분 프로젝트의 정체성을 결정합니다. " +
    "저는 이 여덟 가지 중에서 지연 예측과 이상 탐지 두 가지를 선택했습니다. 둘 다 관제사의 실시간 의사결정에 직접 기여하기 때문입니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 20 · 제가 만든 것
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 06 · OUR PROJECT", "제가 만든 것", "3 integrated features on one pipeline");

  const ours = [
    {
      n: 1, icon: "⏱", ko: "지연 예측 + 신뢰구간", en: "Delay prediction + Conformal interval",
      bullets: [
        "XGBoost · Test R² 0.43",
        "Conformal 90% 커버리지 보장",
        "\"90% 확률로 6 ~ 41 분\"",
      ],
      color: C.skyBlue,
    },
    {
      n: 2, icon: "⚠", ko: "이상 탐지 (7 단계별)", en: "Per-phase anomaly detection × 7",
      bullets: [
        "Isolation Forest × 7 단계",
        "alert fatigue −67%",
        "hysteresis + suppression",
      ],
      color: C.coral,
    },
    {
      n: 3, icon: "🤖", ko: "AI 관제 어시스턴트", en: "AI ATC copilot (LLM + RAG)",
      bullets: [
        "Qwen2.5-7B + QLoRA + DPO",
        "RAG · 161 chunks 규정집",
        "5 초 이내 출처 포함 답변",
      ],
      color: C.teal,
    },
  ];

  ours.forEach((f, i) => {
    const x = 0.5 + i * 3.0;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 1.1, w: 2.85, h: 3.9, fill: { color: C.white }, line: { color: f.color, width: 2 }, rectRadius: 0.12,
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 1.1, w: 2.85, h: 0.5, fill: { color: f.color }, line: { color: f.color },
    });
    s.addText(`${f.n}.`, {
      x, y: 1.1, w: 0.5, h: 0.5, fontSize: 16, bold: true, color: C.white,
      fontFace: FONT_T, align: "center", valign: "middle", margin: 0,
    });
    s.addText(f.icon, {
      x: x + 0.7, y: 1.7, w: 1.45, h: 0.9, fontSize: 46, align: "center", valign: "middle",
      fontFace: FONT_T, margin: 0,
    });
    s.addText(f.ko, {
      x: x + 0.15, y: 2.7, w: 2.55, h: 0.4, fontSize: 13, bold: true, color: C.navy,
      fontFace: FONT_T, align: "center", margin: 0,
    });
    s.addText(f.en, {
      x: x + 0.15, y: 3.08, w: 2.55, h: 0.3, fontSize: 9.5, italic: true, color: f.color,
      fontFace: FONT_B, align: "center", margin: 0,
    });
    f.bullets.forEach((b, j) => {
      s.addText("• " + b, {
        x: x + 0.2, y: 3.5 + j * 0.42, w: 2.5, h: 0.38, fontSize: 10.5, color: C.slate,
        fontFace: FONT_B, margin: 0,
      });
    });
  });

  addFooter(s, 20);
  s.addNotes(
    "제가 직접 만든 세 가지 기능을 한 슬라이드에 모았습니다. " +
    "첫 번째는 지연 예측과 신뢰구간으로, XGBoost Test R² 0.43 에 Conformal 이 90 퍼센트 커버리지를 보장하며, 관제사는 '90 퍼센트 확률로 6 분에서 41 분 사이' 같은 정량적 정보를 받습니다. " +
    "두 번째는 비행 단계별 이상 탐지로, Isolation Forest 일곱 개를 운영해 alert fatigue 를 67 퍼센트 줄였습니다. " +
    "세 번째는 AI 관제 어시스턴트로, Qwen2.5-7B 를 QLoRA 와 DPO 로 직접 파인튜닝한 한국어 LLM 이고 RAG 로 161 개 chunks 규정집을 참조해 5 초 이내에 출처 포함 답변을 생성합니다. " +
    "세 기능이 독립적으로 보이지만 모두 같은 Iceberg 기반 데이터 파이프라인 위에 올라가 있습니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 21 · Why XGBoost?
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 07 · MODELS", "모델 1 · 왜 XGBoost?", "Model 1 · Why XGBoost for delay prediction?");

  const reasons = [
    { icon: "🎯", ko: "정확도",      en: "Accuracy",       desc: "tabular 에서 딥러닝 동등/우위\nmatches or beats DL on tabular", color: C.coral },
    { icon: "⚡", ko: "속도",         en: "Speed",          desc: "5.7M 행 / 4분 CPU\n5.7M rows / 4min CPU", color: C.amber },
    { icon: "🔍", ko: "해석성",      en: "Explainability", desc: "SHAP TreeExplainer\nfeature 별 기여도", color: C.teal },
    { icon: "💪", ko: "Robustness", en: "Robustness",     desc: "NaN 자동 처리\n이상치·스케일 무관", color: C.skyBlue },
  ];

  reasons.forEach((r, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.5 + col * 4.65;
    const y = 1.1 + row * 1.95;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y, w: 4.4, h: 1.8, fill: { color: C.white }, line: { color: r.color, width: 2 }, rectRadius: 0.1,
    });
    s.addText(r.icon, {
      x: x + 0.15, y: y + 0.25, w: 1.0, h: 1.2, fontSize: 50, align: "center", valign: "middle",
      fontFace: FONT_T, margin: 0,
    });
    numberedCircle(s, i + 1, x + 0.1, y + 0.1, r.color);
    s.addText(r.ko, {
      x: x + 1.3, y: y + 0.25, w: 3.0, h: 0.4, fontSize: 18, bold: true, color: C.navy,
      fontFace: FONT_T, margin: 0,
    });
    s.addText(r.en, {
      x: x + 1.3, y: y + 0.65, w: 3.0, h: 0.3, fontSize: 11, italic: true, color: r.color,
      fontFace: FONT_B, margin: 0,
    });
    s.addText(r.desc, {
      x: x + 1.3, y: y + 0.98, w: 3.0, h: 0.7, fontSize: 10.5, color: C.slate,
      fontFace: FONT_B, margin: 0,
    });
  });

  addFooter(s, 21);
  s.addNotes(
    "지연 예측 모델로 XGBoost 를 선택한 이유가 네 가지 있습니다. " +
    "첫째는 정확도로 tabular 데이터에서는 딥러닝과 동등하거나 더 낫고, 피처가 30 개 이하인 tabular 는 XGBoost 의 홈그라운드입니다. " +
    "둘째는 속도로 오백칠십만 행을 CPU 만으로 4 분 안에 학습할 수 있어 GPU 가 필요 없습니다. " +
    "셋째는 해석성으로 SHAP TreeExplainer 를 쓰면 피처별 기여도를 시각화해서 관제사에게 근거를 제시할 수 있고, " +
    "넷째는 robustness 로 결측값을 자동 처리하고 이상치에 강하며 normalization 이 필요 없습니다. " +
    "실무에서 가장 중요한 것은 세 번째 해석성입니다. 딥러닝 블랙박스로는 관제사의 '왜?' 에 납득할 만한 답을 줄 수 없습니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 22 · XGBoost 작동 원리 (Gradient Boosting)
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 07 · MODELS", "XGBoost 작동 원리", "How Gradient Boosting Actually Works");

  s.addText("💡 한 문장 요약", {
    x: 0.5, y: 1.05, w: 9, h: 0.3, fontSize: 12, bold: true, color: C.amber, fontFace: FONT_T, margin: 0,
  });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 1.35, w: 8.9, h: 0.7, fill: { color: C.ice }, line: { color: C.skyBlue, width: 1 }, rectRadius: 0.08,
  });
  s.addText([
    { text: "여러 개의 '약한 모델' 을 순차적으로 만들되, ", options: { color: C.navy, fontSize: 12 } },
    { text: "이전 모델의 오차에만 집중", options: { color: C.coral, fontSize: 12, bold: true } },
    { text: "해 학습\n", options: { color: C.navy, fontSize: 12 } },
    { text: "Build many weak models sequentially, each focusing only on the previous model's errors",
      options: { color: C.mute, fontSize: 9.5, italic: true } },
  ], {
    x: 0.7, y: 1.4, w: 8.6, h: 0.65, fontFace: FONT_B, margin: 0, valign: "middle",
  });

  // Tree sequence visualization
  const trees = [
    { n: 1, err: "±15 분", pred: "예측: 10 분", color: C.coral },
    { n: 2, err: "±8 분",  pred: "잔차에 집중", color: C.amber },
    { n: 3, err: "±3 분",  pred: "더 세밀하게",  color: C.teal },
    { n: "...", err: "±0.5분", pred: "n=200 까지", color: C.green },
  ];

  trees.forEach((t, i) => {
    const x = 0.5 + i * 2.3;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 2.3, w: 2.0, h: 1.6, fill: { color: C.white }, line: { color: t.color, width: 1.5 }, rectRadius: 0.08,
    });
    s.addText("🌳", {
      x, y: 2.35, w: 2.0, h: 0.5, fontSize: 30, align: "center", valign: "middle", fontFace: FONT_T, margin: 0,
    });
    s.addText(`Tree ${t.n}`, {
      x, y: 2.85, w: 2.0, h: 0.3, fontSize: 12, bold: true, color: t.color,
      fontFace: FONT_T, align: "center", margin: 0,
    });
    s.addText(t.pred, {
      x: x + 0.1, y: 3.2, w: 1.8, h: 0.28, fontSize: 10, color: C.navy,
      fontFace: FONT_B, align: "center", margin: 0,
    });
    s.addText("오차: " + t.err, {
      x: x + 0.1, y: 3.48, w: 1.8, h: 0.28, fontSize: 9.5, italic: true, color: C.mute,
      fontFace: FONT_B, align: "center", margin: 0,
    });
    if (i < trees.length - 1) {
      s.addText("+", {
        x: x + 2.0, y: 2.8, w: 0.3, h: 0.6, fontSize: 18, bold: true, color: C.amber,
        align: "center", valign: "middle", margin: 0,
      });
    }
  });

  // 결과 방정식
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 4.1, w: 8.9, h: 0.95, fill: { color: C.navy }, line: { color: C.navy }, rectRadius: 0.08,
  });
  s.addText("최종 예측 =  Tree₁  +  Tree₂  +  Tree₃  +  ...  +  Tree₂₀₀", {
    x: 0.5, y: 4.15, w: 8.9, h: 0.4, fontSize: 15, bold: true, color: C.white,
    fontFace: FONT_M, align: "center", margin: 0,
  });
  s.addText("Final prediction = sum of all weak learners · residual boosting", {
    x: 0.5, y: 4.55, w: 8.9, h: 0.4, fontSize: 10, italic: true, color: C.amber,
    fontFace: FONT_B, align: "center", margin: 0,
  });

  addFooter(s, 22);
  s.addNotes(
    "XGBoost 는 여러 개의 약한 모델을 순차적으로 만들되, 이전 모델의 오차에만 집중해서 학습합니다. " +
    "Tree 1 은 오차가 플러스마이너스 15 분 정도로 엉성하지만, Tree 2 가 남은 잔차에 집중해 플러스마이너스 8 분으로 줄이고, Tree 3 이 또 남은 오차에 집중해 플러스마이너스 3 분까지 내려옵니다. " +
    "이렇게 200 번까지 반복하면 최종 오차는 플러스마이너스 0.5 분 수준이 되고, 최종 예측은 Tree 1 부터 Tree 200 까지의 합이 됩니다. " +
    "시험 공부할 때 틀린 문제만 다시 보는 것과 같은 원리입니다. 70 퍼센트 맞추면 틀린 30 퍼센트만 집중하고, 그중 또 틀린 것만 집중하는 방식입니다. " +
    "이것이 gradient boosting 이라는 이름의 의미이고, 매 단계 손실 함수의 기울기를 따라 최적으로 수정해 나갑니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 23 · XGBoost 결과
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 07 · MODELS", "XGBoost 실제 결과", "XGBoost actual results · sprint progression");

  // Bar chart: R² over sprints
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 1.05, w: 8.9, h: 2.9, fill: { color: C.white }, line: { color: C.slate, width: 1 }, rectRadius: 0.08,
  });
  s.addText("Test R² 추이 (Sprint 별)", {
    x: 0.7, y: 1.1, w: 8.6, h: 0.3, fontSize: 12, bold: true, color: C.navy, fontFace: FONT_T, margin: 0,
  });

  const bars = [
    { label: "기본 XGBoost\nbaseline",      val: 0.10, color: C.coral },
    { label: "+ TimeSeriesSplit\nP0",       val: 0.10, color: C.amber },
    { label: "+ Rotation ★\nP1",            val: 0.43, color: C.green },
    { label: "+ Conformal\nP1+",            val: 0.43, color: C.teal },
  ];
  const maxBarH = 2.0;
  const maxVal = 0.5;
  bars.forEach((b, i) => {
    const x = 0.8 + i * 2.15;
    const h = (b.val / maxVal) * maxBarH;
    const barY = 3.7 - h;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: barY, w: 1.6, h, fill: { color: b.color }, line: { color: b.color },
    });
    s.addText(b.val.toFixed(2), {
      x, y: barY - 0.35, w: 1.6, h: 0.3, fontSize: 14, bold: true, color: b.color,
      fontFace: FONT_T, align: "center", margin: 0,
    });
    s.addText(b.label, {
      x, y: 3.75, w: 1.6, h: 0.45, fontSize: 9, color: C.slate, fontFace: FONT_B, align: "center", margin: 0,
    });
  });
  s.addShape(pres.shapes.LINE, {
    x: 0.5, y: 3.7, w: 8.9, h: 0, line: { color: C.slate, width: 1 },
  });

  // Final metrics
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 4.15, w: 8.9, h: 0.9, fill: { color: C.navy }, line: { color: C.navy }, rectRadius: 0.08,
  });
  const metrics = [
    ["Test RMSE",    "22.61 분",  "Val RMSE"],
    ["Test R²",      "0.43",      "분류 정확도"],
    ["Conformal",    "90.00 %",   "Empirical coverage"],
    ["응답 시간",    "42 ms",     "p95 latency"],
  ];
  metrics.forEach((m, i) => {
    const x = 0.6 + i * 2.2;
    s.addText(m[0], {
      x, y: 4.23, w: 2.1, h: 0.22, fontSize: 9, italic: true, color: C.amber,
      fontFace: FONT_B, align: "center", margin: 0,
    });
    s.addText(m[1], {
      x, y: 4.48, w: 2.1, h: 0.32, fontSize: 16, bold: true, color: C.white,
      fontFace: FONT_T, align: "center", margin: 0,
    });
    s.addText(m[2], {
      x, y: 4.82, w: 2.1, h: 0.2, fontSize: 8, italic: true, color: C.ice,
      fontFace: FONT_B, align: "center", margin: 0,
    });
  });

  addFooter(s, 23);
  s.addNotes(
    "실제 제 프로젝트의 결과를 Sprint 별 Test R² 추이로 보여드립니다. " +
    "기본 XGBoost baseline 은 R² 0.10, TimeSeriesSplit 을 적용한 P0 도 R² 0.10 으로 수치는 그대로지만 정직해졌습니다. " +
    "Rotation features 를 추가한 P1 에서 R² 가 0.43 으로 뛰었고, Conformal interval 을 붙인 P1+ 도 R² 0.43 을 유지하면서 예측 구간이 추가됐습니다. " +
    "P0 에서 수치가 안 올라간 이유는 TimeSeriesSplit 이 더 좋은 모델을 만드는 게 아니라 더 정직한 평가를 해주는 기법이기 때문입니다. " +
    "진짜 향상은 P1 의 Rotation features 가 만들어냈습니다. " +
    "최종 지표는 Test RMSE 22.61 분, Test R² 0.43, Conformal coverage 정확히 90.00 퍼센트, p95 응답 시간 42 밀리세컨드입니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 24 · Why Isolation Forest?
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 07 · MODELS", "모델 2 · 왜 Isolation Forest?", "Model 2 · Why Isolation Forest for anomaly?");

  // Core idea
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 1.05, w: 8.9, h: 0.85, fill: { color: C.navy }, line: { color: C.navy }, rectRadius: 0.08,
  });
  s.addText([
    { text: "핵심 아이디어: ", options: { bold: true, color: C.amber, fontSize: 13 } },
    { text: "\"이상치는 소수이고 정상과 거리가 멀어서, ", options: { color: C.white, fontSize: 12 } },
    { text: "무작위 분할로 빨리 고립", options: { color: C.coral, fontSize: 12, bold: true } },
    { text: "된다\"\n", options: { color: C.white, fontSize: 12 } },
    { text: "Anomalies are few and far — they get 'isolated' quickly under random partitioning",
      options: { italic: true, color: C.ice, fontSize: 10 } },
  ], {
    x: 0.7, y: 1.1, w: 8.6, h: 0.75, fontFace: FONT_B, margin: 0, valign: "middle",
  });

  // Visual: path length for normal vs anomaly
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 2.05, w: 4.4, h: 2.0, fill: { color: C.white }, line: { color: C.green, width: 1.5 }, rectRadius: 0.08,
  });
  s.addText("정상점 (normal)", {
    x: 0.5, y: 2.1, w: 4.4, h: 0.3, fontSize: 12, bold: true, color: C.green, fontFace: FONT_T, align: "center", margin: 0,
  });
  s.addText("🌳 🌳 🌳 🌳 🌳 🌳 🌳", {
    x: 0.5, y: 2.5, w: 4.4, h: 0.5, fontSize: 20, align: "center", valign: "middle", fontFace: FONT_T, margin: 0,
  });
  s.addText("path length = 깊음\npath length = deep (8+ splits)\n분할을 많이 해야 고립됨", {
    x: 0.5, y: 3.1, w: 4.4, h: 0.85, fontSize: 10.5, color: C.slate,
    fontFace: FONT_B, align: "center", margin: 0,
  });

  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 5.1, y: 2.05, w: 4.3, h: 2.0, fill: { color: C.white }, line: { color: C.coral, width: 1.5 }, rectRadius: 0.08,
  });
  s.addText("이상점 (anomaly)", {
    x: 5.1, y: 2.1, w: 4.3, h: 0.3, fontSize: 12, bold: true, color: C.coral, fontFace: FONT_T, align: "center", margin: 0,
  });
  s.addText("🌳 🌳", {
    x: 5.1, y: 2.5, w: 4.3, h: 0.5, fontSize: 20, align: "center", valign: "middle", fontFace: FONT_T, margin: 0,
  });
  s.addText("path length = 얕음\npath length = shallow (2-3 splits)\n빨리 고립됨 → anomaly score 높음", {
    x: 5.1, y: 3.1, w: 4.3, h: 0.85, fontSize: 10.5, color: C.slate,
    fontFace: FONT_B, align: "center", margin: 0,
  });

  // Why IF over alternatives
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 4.15, w: 8.9, h: 0.9, fill: { color: C.ice }, line: { color: C.skyBlue, width: 1 }, rectRadius: 0.08,
  });
  s.addText([
    { text: "🎯 라벨 없음 ", options: { bold: true, color: C.skyBlue, fontSize: 11 } },
    { text: "(no labels) · 항공 사고는 희귀해서 지도학습 불가\n", options: { color: C.slate, fontSize: 10 } },
    { text: "⚡ O(n log n) · ", options: { bold: true, color: C.skyBlue, fontSize: 11 } },
    { text: "Autoencoder/One-class SVM 보다 훨씬 빠름\n", options: { color: C.slate, fontSize: 10 } },
    { text: "🧠 직관적 ", options: { bold: true, color: C.skyBlue, fontSize: 11 } },
    { text: "· path length 가 곧 anomaly score — 해석 가능", options: { color: C.slate, fontSize: 10 } },
  ], {
    x: 0.7, y: 4.2, w: 8.6, h: 0.8, fontFace: FONT_B, margin: 0, valign: "middle",
  });

  addFooter(s, 24);
  s.addNotes(
    "두 번째 모델은 이상 탐지용 Isolation Forest 입니다. " +
    "핵심 아이디어는 이상치가 소수이고 정상과 거리가 멀기 때문에 무작위 분할로 빨리 고립된다는 점입니다. " +
    "정상점은 트리에서 깊이 내려가야 고립되어 path length 가 8 스플리츠 이상 필요한 반면, 이상점은 단 2 번에서 3 번의 분할로 곧바로 고립됩니다. " +
    "즉 path length 자체가 anomaly score 가 됩니다. 짧으면 이상, 길면 정상이라 매우 직관적입니다. " +
    "Isolation Forest 를 선택한 이유는 항공 사고가 희귀해 라벨이 없기에 지도학습이 불가능하고, 빅오 엔 로그 엔 속도로 매우 빠르며, 해석이 직관적이기 때문입니다. " +
    "Autoencoder 를 선택했다면 GPU 필요, 학습 불안정, 블랙박스 세 문제가 모두 생겼을 겁니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 25 · Per-phase IF × 7
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 07 · MODELS", "Per-phase IF × 7 — 단계별 분리", "Why 7 models instead of 1?");

  // Problem — 단일 모델의 혼동
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 1.05, w: 8.9, h: 1.3, fill: { color: C.white }, line: { color: C.coral, width: 1.5 }, rectRadius: 0.08,
  });
  s.addText("❌ 단일 모델의 혼동 (single-model confusion)", {
    x: 0.7, y: 1.1, w: 8.6, h: 0.3, fontSize: 12, bold: true, color: C.coral, fontFace: FONT_T, margin: 0,
  });
  s.addText([
    { text: "CRUISE 중 30,000 ft 는 ", options: { color: C.slate, fontSize: 11 } },
    { text: "정상", options: { color: C.green, bold: true, fontSize: 11 } },
    { text: "인데, LANDING 중 30,000 ft 는 ", options: { color: C.slate, fontSize: 11 } },
    { text: "완전 비정상", options: { color: C.coral, bold: true, fontSize: 11 } },
    { text: ".\n단일 모델은 둘을 구분 못해 → TAXI 급가속 = CRUISE threshold 위반 → false positive\n",
      options: { color: C.slate, fontSize: 11 } },
    { text: "30,000 ft during CRUISE = normal, but same altitude during LANDING = abnormal. " +
            "Single model can't tell them apart → alert fatigue.",
      options: { italic: true, color: C.mute, fontSize: 9.5 } },
  ], {
    x: 0.7, y: 1.4, w: 8.6, h: 0.95, fontFace: FONT_B, margin: 0,
  });

  // 7 phases with different contamination
  const phases = [
    { name: "TAXI",     contam: "0.02", color: C.slate },
    { name: "TAKEOFF",  contam: "0.03", color: C.amber },
    { name: "CLIMB",    contam: "0.04", color: C.teal },
    { name: "CRUISE",   contam: "0.05", color: C.skyBlue },
    { name: "DESCENT",  contam: "0.04", color: C.purple },
    { name: "APPROACH", contam: "0.06", color: C.coral },
    { name: "LANDING",  contam: "0.06", color: C.coral },
  ];
  s.addText("✅ 해결: 단계별로 7개 모델 + contamination 별도 튜닝", {
    x: 0.5, y: 2.5, w: 9, h: 0.3, fontSize: 12, bold: true, color: C.green, fontFace: FONT_T, margin: 0,
  });
  phases.forEach((p, i) => {
    const x = 0.5 + i * 1.28;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 2.85, w: 1.2, h: 1.2, fill: { color: C.white }, line: { color: p.color, width: 2 }, rectRadius: 0.08,
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 2.85, w: 1.2, h: 0.32, fill: { color: p.color }, line: { color: p.color },
    });
    s.addText(p.name, {
      x, y: 2.85, w: 1.2, h: 0.32, fontSize: 8.5, bold: true, color: C.white,
      fontFace: FONT_T, align: "center", valign: "middle", margin: 0,
    });
    s.addText("🌳", {
      x, y: 3.2, w: 1.2, h: 0.45, fontSize: 22, align: "center", valign: "middle", fontFace: FONT_T, margin: 0,
    });
    s.addText("contam", {
      x, y: 3.65, w: 1.2, h: 0.18, fontSize: 8, color: C.mute, italic: true,
      fontFace: FONT_B, align: "center", margin: 0,
    });
    s.addText(p.contam, {
      x, y: 3.82, w: 1.2, h: 0.2, fontSize: 11, bold: true, color: p.color,
      fontFace: FONT_M, align: "center", margin: 0,
    });
  });

  // 결과 badge
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 4.2, w: 8.9, h: 0.82, fill: { color: C.navy }, line: { color: C.navy }, rectRadius: 0.08,
  });
  s.addText([
    { text: "📉 결과: ", options: { bold: true, color: C.amber, fontSize: 12 } },
    { text: "False Positive ", options: { color: C.white, fontSize: 12 } },
    { text: "−67 %", options: { bold: true, color: C.green, fontSize: 16 } },
    { text: "  ·  alert fatigue 대폭 완화  ·  v2.1.10 serving 에 실제 wire-up (ADR-006)",
      options: { color: C.white, fontSize: 11 } },
  ], {
    x: 0.7, y: 4.28, w: 8.6, h: 0.65, fontFace: FONT_B, margin: 0, valign: "middle",
  });

  addFooter(s, 25);
  s.addNotes(
    "Isolation Forest 를 하나가 아니라 일곱 개 만든 이유는, 단일 모델이 비행 단계별 차이를 구분하지 못하기 때문입니다. " +
    "CRUISE 중 3만 피트는 정상이지만 LANDING 중 3만 피트는 완전 비정상인데, 단일 모델은 이 둘을 구분 못하고 false positive 가 폭주하며 alert fatigue 를 유발합니다. " +
    "해결책으로 일곱 개의 비행 단계마다 별도 Isolation Forest 를 두고 contamination 을 개별 튜닝했습니다. " +
    "TAXI 는 조용한 구간이라 0.02, TAKEOFF 0.03, CLIMB 0.04, CRUISE 0.05, DESCENT 0.04, APPROACH 와 LANDING 은 사고 빈발 구간이라 0.06 까지, TAXI 의 2 퍼센트부터 LANDING 의 6 퍼센트까지 3 배 차이로 튜닝했습니다. " +
    "결과적으로 False Positive 가 67 퍼센트 감소하며 alert fatigue 가 대폭 완화됐고, v2.1.10 과 ADR-006 에서 서빙에도 wire-up 이 완료됐습니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 26 · Conformal Prediction
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 07 · MODELS", "Conformal Prediction — 점 vs 구간", "Point estimate vs Interval prediction");

  // Left: point estimate
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 1.05, w: 4.3, h: 3.9, fill: { color: C.white }, line: { color: C.coral, width: 2 }, rectRadius: 0.1,
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.05, w: 4.3, h: 0.45, fill: { color: C.coral }, line: { color: C.coral },
  });
  s.addText("❌  BEFORE  ·  점 예측만", {
    x: 0.5, y: 1.05, w: 4.3, h: 0.45, fontSize: 12, bold: true, color: C.white,
    fontFace: FONT_T, align: "center", valign: "middle", margin: 0,
  });
  s.addText("🎯", {
    x: 0.5, y: 1.7, w: 4.3, h: 0.8, fontSize: 50, align: "center", valign: "middle", fontFace: FONT_T, margin: 0,
  });
  s.addText("\"15 분 지연\"", {
    x: 0.5, y: 2.6, w: 4.3, h: 0.5, fontSize: 22, bold: true, color: C.navy,
    fontFace: FONT_T, align: "center", margin: 0,
  });
  s.addText("\"15 min delay\"", {
    x: 0.5, y: 3.1, w: 4.3, h: 0.28, fontSize: 11, italic: true, color: C.mute,
    fontFace: FONT_B, align: "center", margin: 0,
  });
  s.addText([
    { text: "💭 얼마나 믿어야 할까?\n", options: { color: C.coral, fontSize: 10.5, bold: true } },
    { text: "실제: 5분일 수도 40분일 수도\n", options: { color: C.slate, fontSize: 10 } },
    { text: "actually could be 5 or 40 min — 근거 없음",
      options: { italic: true, color: C.mute, fontSize: 9 } },
  ], {
    x: 0.7, y: 3.55, w: 3.9, h: 1.3, fontFace: FONT_B, margin: 0, align: "center",
  });

  // Right: conformal interval
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 5.2, y: 1.05, w: 4.3, h: 3.9, fill: { color: C.white }, line: { color: C.green, width: 2 }, rectRadius: 0.1,
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: 1.05, w: 4.3, h: 0.45, fill: { color: C.green }, line: { color: C.green },
  });
  s.addText("✅  AFTER  ·  신뢰구간 (Conformal)", {
    x: 5.2, y: 1.05, w: 4.3, h: 0.45, fontSize: 12, bold: true, color: C.white,
    fontFace: FONT_T, align: "center", valign: "middle", margin: 0,
  });
  // Draw interval bar
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.5, y: 1.9, w: 3.7, h: 0.6, fill: { color: C.ice }, line: { color: C.green, width: 1 },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.9, y: 2.0, w: 2.9, h: 0.4, fill: { color: C.green }, line: { color: C.green },
  });
  s.addText("6", { x: 5.7, y: 2.5, w: 0.4, h: 0.25, fontSize: 11, bold: true, color: C.green, fontFace: FONT_M, align: "center", margin: 0 });
  s.addText("41", { x: 8.55, y: 2.5, w: 0.4, h: 0.25, fontSize: 11, bold: true, color: C.green, fontFace: FONT_M, align: "center", margin: 0 });
  s.addText("min", { x: 6.0, y: 2.85, w: 2.8, h: 0.22, fontSize: 9, italic: true, color: C.mute, fontFace: FONT_B, align: "center", margin: 0 });

  s.addText("\"6 ~ 41 분 지연\"", {
    x: 5.2, y: 3.15, w: 4.3, h: 0.45, fontSize: 19, bold: true, color: C.navy,
    fontFace: FONT_T, align: "center", margin: 0,
  });
  s.addText("at 90% confidence · MAPIE empirical 90.00%", {
    x: 5.2, y: 3.62, w: 4.3, h: 0.28, fontSize: 10, italic: true, color: C.green,
    fontFace: FONT_B, align: "center", margin: 0,
  });
  s.addText([
    { text: "🎯 수학적으로 보장된 커버리지\n", options: { color: C.green, fontSize: 10.5, bold: true } },
    { text: "관제사: \"최악의 경우 41분까지 가능\"\n", options: { color: C.slate, fontSize: 10 } },
    { text: "ATC can plan for worst case → quantified decision",
      options: { italic: true, color: C.mute, fontSize: 9 } },
  ], {
    x: 5.4, y: 4.05, w: 3.9, h: 0.85, fontFace: FONT_B, margin: 0, align: "center",
  });

  addFooter(s, 26);
  s.addNotes(
    "마지막 핵심 기법은 점 예측과 구간 예측의 차이입니다. " +
    "'15 분 지연' 이라는 점 예측은 얼마나 믿어야 할지 알 수 없고, 실제로는 5 분일 수도 40 분일 수도 있습니다. " +
    "관제사가 이 숫자만 보고 승객 안내를 어떻게 하겠습니까. 근거 없는 high, medium, low confidence 분류로는 부족합니다. " +
    "Conformal 을 적용한 후에는 '90 퍼센트 확률로 6 분에서 41 분 사이의 지연' 이라는 수학적으로 보장된 구간을 얻을 수 있고, 그것도 분포 가정 없이 보장됩니다. " +
    "MAPIE 라이브러리로 구현했고 실측 coverage 가 정확히 90.00 퍼센트로 나온 것이 증거입니다. " +
    "이제 관제사는 최악의 경우 41 분까지 지연 가능하니 승객 안내를 준비하자는 정량적 의사결정을 할 수 있습니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 27 · Data to Decision end-to-end
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 08 · END-TO-END", "데이터 → 의사결정", "Data to Decision — a live example");

  const flow = [
    { n: 1, icon: "✈️", ko: "ADS-B 수신",        data: "icao=a1b2c3\nalt=10668 m",       color: C.skyBlue },
    { n: 2, icon: "📨", ko: "Kafka 도착",         data: "flight-position\nAvro v2.0",    color: C.teal },
    { n: 3, icon: "🧊", ko: "Iceberg Silver",    data: "flight_features\n25 cols",       color: C.slate },
    { n: 4, icon: "🌳", ko: "XGBoost 예측",       data: "delay = 20 min\nR² 0.43",        color: C.amber },
    { n: 5, icon: "🎯", ko: "Conformal 구간",     data: "[12, 40] min\n90% conf",         color: C.green },
    { n: 6, icon: "🤖", ko: "RAG + LLM 조언",     data: "\"승객 안내 준비\nFAA AIM 7-1\"",  color: C.purple },
    { n: 7, icon: "🖥", ko: "관제사 대시보드",   data: "<5s 전체 지연\n<42ms 서빙",       color: C.coral },
  ];

  flow.forEach((f, i) => {
    const col = i % 4;
    const row = Math.floor(i / 4);
    const x = 0.5 + col * 2.25;
    const y = 1.1 + row * 1.95;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y, w: 2.1, h: 1.75, fill: { color: C.white }, line: { color: f.color, width: 1.5 }, rectRadius: 0.08,
    });
    numberedCircle(s, f.n, x + 0.1, y + 0.1, f.color);
    s.addText(f.icon, {
      x, y: y + 0.1, w: 2.1, h: 0.7, fontSize: 32, align: "center", valign: "middle", fontFace: FONT_T, margin: 0,
    });
    s.addText(f.ko, {
      x, y: y + 0.8, w: 2.1, h: 0.35, fontSize: 12, bold: true, color: C.navy,
      fontFace: FONT_T, align: "center", margin: 0,
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: x + 0.1, y: y + 1.2, w: 1.9, h: 0.5, fill: { color: C.ice }, line: { color: f.color, width: 0.5 },
    });
    s.addText(f.data, {
      x: x + 0.15, y: y + 1.22, w: 1.8, h: 0.48, fontSize: 8.5, color: f.color,
      fontFace: FONT_M, align: "center", valign: "middle", margin: 0,
    });
    // arrows
    if (i % 4 !== 3 && i < flow.length - 1) {
      s.addText("→", {
        x: x + 2.1, y, w: 0.2, h: 1.75, fontSize: 20, bold: true, color: C.amber,
        align: "center", valign: "middle", margin: 0,
      });
    }
  });

  addFooter(s, 27);
  s.addNotes(
    "모든 조각을 하나로 연결해 보겠습니다. 비행기가 공중에 떠 있는 순간부터 관제사 화면에 알림이 뜨는 순간까지 일곱 단계가 5 초 이내에 흐릅니다. " +
    "ADS-B 수신에서 비행기 위치가 OpenSky 로 오고, Kafka 의 flight-position 토픽에 Avro 메시지가 쌓입니다. " +
    "Iceberg Silver 의 flight_features 에서 조인하고, XGBoost 가 42 밀리세컨드 안에 '지연 20 분' 을 예측합니다. " +
    "Conformal 이 '90 퍼센트 확률로 12 분에서 40 분' 구간을 계산하고, RAG 와 LLM 이 FAA AIM 7-1 에 따른 출처 기반 조언을 생성해서 관제사 대시보드에 표시합니다. " +
    "Kafka 약 100 밀리세컨드, Iceberg 500 밀리세컨드, XGBoost 42 밀리세컨드, Conformal 100 밀리세컨드, LLM 2 초에서 3 초가 걸리고, LLM 이 가장 느린 병목입니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 28 · Key Takeaways
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 09 · TAKEAWAYS", "학생을 위한 핵심 교훈", "Key Takeaways for Students");

  const tks = [
    { ko: "데이터는 raw 부터 완벽하지 않다", en: "Raw data is never clean",
      detail: "cleaning 단계를 절대 건너뛰지 마라", color: C.coral },
    { ko: "Feature engineering > 모델 크기",  en: "Features > Model size",
      detail: "실제: 5 features 추가로 R² +335% (P1)", color: C.amber },
    { ko: "시계열은 절대 shuffle 하지 마라",  en: "Never shuffle time-series",
      detail: "Temporal leakage 는 가장 흔한 치명적 실수", color: C.teal },
    { ko: "모델 선택은 정확도만이 아니다",    en: "Accuracy is not the only metric",
      detail: "해석성 · 운영성 · 유지비 모두 고려", color: C.skyBlue },
    { ko: "도메인 지식이 곧 경쟁력",           en: "Domain knowledge = competitive edge",
      detail: "EUROCONTROL 연구 → Rotation feature 설계", color: C.purple },
  ];

  tks.forEach((t, i) => {
    const y = 1.15 + i * 0.77;
    numberedCircle(s, i + 1, 0.55, y + 0.05, t.color);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 1.35, y, w: 8.15, h: 0.65, fill: { color: C.white },
      line: { color: t.color, width: 1.5 }, rectRadius: 0.08,
    });
    s.addText(t.ko, {
      x: 1.5, y: y + 0.02, w: 8, h: 0.3, fontSize: 13, bold: true, color: C.navy,
      fontFace: FONT_T, margin: 0,
    });
    s.addText([
      { text: t.en, options: { italic: true, color: t.color, fontSize: 10, bold: true } },
      { text: "  —  " + t.detail, options: { color: C.mute, fontSize: 10, italic: true } },
    ], {
      x: 1.5, y: y + 0.33, w: 8, h: 0.3, fontFace: FONT_B, margin: 0,
    });
  });

  addFooter(s, 28);
  s.addNotes(
    "이 발표에서 여러분이 가져가셨으면 하는 다섯 가지 교훈입니다. " +
    "첫 번째, 데이터는 raw 단계에서 절대 완벽하지 않으니 cleaning 을 건너뛰지 마십시오. " +
    "두 번째, Feature Engineering 이 모델 크기보다 중요합니다. 제 프로젝트의 P1 에서 피처 다섯 개만 추가해 R² 가 335 퍼센트 개선됐습니다. " +
    "세 번째, 시계열 데이터는 절대 shuffle 하지 마십시오. temporal leakage 는 가장 흔하면서도 가장 치명적인 실수입니다. " +
    "네 번째, 모델 선택을 정확도만으로 하지 말고 해석성과 운영성, 유지 비용을 모두 고려하십시오. " +
    "다섯 번째, 도메인 지식이 곧 경쟁력입니다. EUROCONTROL 의 '지연 45 퍼센트는 reactionary 다' 라는 연구 한 줄이 Rotation features 설계의 씨앗이 됐습니다. " +
    "특히 두 번째와 세 번째가 초심자가 가장 많이 실패하는 지점입니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 29 · Q&A
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.navy };
  addHeader(s, "CHAPTER 10 · DISCUSSION", "질문 & 토론", "Q&A — questions for discussion");

  s.addText("💬", {
    x: 0.5, y: 1.0, w: 9, h: 0.9, fontSize: 60, align: "center", valign: "middle",
    color: C.white, fontFace: FONT_T, margin: 0,
  });

  const questions = [
    { q: "왜 Iceberg 가 그냥 parquet 보다 낫나요?",
      en: "Why Iceberg over plain parquet?", color: C.skyBlue },
    { q: "Conformal 말고 Bayesian CI 는 안 되나요?",
      en: "Why not Bayesian credible interval?", color: C.teal },
    { q: "Per-phase 7개 대신 phase 를 feature 로 넣으면?",
      en: "Why not just use phase as a feature?", color: C.amber },
    { q: "5.7M 행 전부 말고 샘플만 써도 되나요?",
      en: "Is 10% sampling OK?", color: C.coral },
    { q: "RAG 161 chunks 로 충분한가요?",
      en: "Is 161 chunks enough for RAG?", color: C.purple },
  ];

  questions.forEach((q, i) => {
    const y = 2.05 + i * 0.58;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 0.8, y, w: 8.4, h: 0.5, fill: { color: C.white }, line: { color: q.color, width: 1 }, rectRadius: 0.08,
    });
    s.addText("Q", {
      x: 0.9, y: y + 0.07, w: 0.4, h: 0.36, fontSize: 14, bold: true, color: q.color,
      fontFace: FONT_T, align: "center", valign: "middle", margin: 0,
    });
    s.addText([
      { text: q.q, options: { bold: true, color: C.navy, fontSize: 11 } },
      { text: "   " + q.en, options: { italic: true, color: C.mute, fontSize: 9 } },
    ], {
      x: 1.4, y: y + 0.03, w: 7.7, h: 0.44, fontFace: FONT_B, margin: 0, valign: "middle",
    });
  });

  addFooter(s, 29);
  s.addNotes(
    "예상 질문 다섯 개에 대한 답변을 준비해 왔습니다. " +
    "첫째, Iceberg 가 plain parquet 보다 나은 이유는 catalog, ACID 트랜잭션, 스키마 진화, time-travel 이 모두 포함된 테이블 포맷이기 때문입니다. " +
    "둘째, Bayesian 은 prior 가정이 필요하지만 Conformal 은 분포 가정 자체가 없어서 데이터가 가정을 어겨도 구간이 깨지지 않습니다. " +
    "셋째, 단일 모델은 contamination 을 모든 phase 에 동일하게 적용해야 해서 TAXI 2 퍼센트와 LANDING 6 퍼센트처럼 3 배 차이가 나는 phase 별 특성을 전혀 반영할 수 없습니다. " +
    "넷째, 10 퍼센트 샘플링은 chronological 하게 뽑아서 시간 편향이 없게 했고, 오십만 행이면 통계적으로 충분합니다. " +
    "다섯째, 161 chunks 는 RAGAs 평가에서 faithfulness 0.91, context_precision 0.85 로 검증됐고 국내선 관제에는 충분합니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 30 · 감사 + 자원
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.navy };

  // 크게
  s.addText("감사합니다", {
    x: 0.5, y: 1.1, w: 9, h: 0.8, fontSize: 52, bold: true, color: C.white,
    fontFace: FONT_T, align: "center", margin: 0,
  });
  s.addText("Thank You — Questions Welcome", {
    x: 0.5, y: 2.0, w: 9, h: 0.4, fontSize: 18, italic: true, color: C.ice,
    fontFace: FONT_B, align: "center", margin: 0,
  });

  // Resources
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 1.0, y: 2.8, w: 8.0, h: 1.95, fill: { color: C.cream }, line: { color: C.amber, width: 1 }, rectRadius: 0.1,
  });
  s.addText("📚  Resources", {
    x: 1.2, y: 2.9, w: 7.6, h: 0.3, fontSize: 13, bold: true, color: C.navy, fontFace: FONT_T, margin: 0,
  });
  const links = [
    ["🐙", "GitHub",       "github.com/biz-doublej/SkyOps-Intelligence"],
    ["📘", "Data docs",    "docs/data_collection.md"],
    ["🧑‍🏫", "Reproduction", "docs/reproduction_guide.md (564 lines)"],
    ["📋", "ADRs 7개",     "docs/adr/ (001~007)"],
    ["📧", "Contact",       "doublej.biz01@gmail.com"],
  ];
  links.forEach((l, i) => {
    const y = 3.25 + i * 0.28;
    s.addText(l[0], {
      x: 1.3, y, w: 0.4, h: 0.24, fontSize: 13, align: "center", valign: "middle",
      fontFace: FONT_T, margin: 0,
    });
    s.addText(l[1], {
      x: 1.75, y, w: 1.8, h: 0.24, fontSize: 11, bold: true, color: C.skyBlue,
      fontFace: FONT_T, margin: 0, valign: "middle",
    });
    s.addText(l[2], {
      x: 3.6, y, w: 5.3, h: 0.24, fontSize: 10, color: C.slate,
      fontFace: FONT_M, margin: 0, valign: "middle",
    });
  });

  // 서명
  s.addText([
    { text: "DoubleJ 팀 / 정재원  ·  ", options: { bold: true, color: C.amber, fontSize: 11 } },
    { text: "빅데이터과 캡스톤디자인  ·  ", options: { color: C.ice, fontSize: 11 } },
    { text: "v2.2.0 · 2026-04-19", options: { color: C.mute, fontSize: 11, italic: true } },
  ], {
    x: 0.5, y: 4.95, w: 9, h: 0.3, fontFace: FONT_B, margin: 0, align: "center",
  });

  s.addNotes(
    "오늘 발표의 핵심 세 가지를 다시 정리드립니다. " +
    "첫째, 데이터는 전처리가 핵심이니 여섯 단계 파이프라인을 기억해 주시기 바랍니다. " +
    "둘째, Feature Engineering 이 모델보다 강력하며 335 퍼센트 개선 사례가 그 증거입니다. " +
    "셋째, 시계열 데이터는 절대 shuffle 하지 마시고, ADR-004 의 원칙을 참고해 주세요. " +
    "질문이 더 있으시면 발표 후에도 편하게 말씀해 주세요. 감사합니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 저장
// ─────────────────────────────────────────────────────────────────
pres.writeFile({ fileName: "SkyOps_Data_교육용_발표자료.pptx" })
  .then((f) => {
    console.log(`✅ 생성 완료: ${f}`);
  })
  .catch((e) => {
    console.error("❌ 오류:", e);
    process.exit(1);
  });
