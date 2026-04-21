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
    "안녕하세요. 오늘은 SkyOps Intelligence 프로젝트의 '데이터'에 집중해서 설명드립니다. " +
    "한국인 학생과 외국인 학생 모두 이해할 수 있도록 한글 설명 옆에 영어 핵심 용어를 병기했습니다. " +
    "총 30 장, 약 25~30 분 예상입니다.\n\n" +
    "Hello. Today's session focuses on the DATA side of SkyOps Intelligence. " +
    "Korean and English key terms are shown side-by-side. 30 slides, ~25-30 min."
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
    "이 5 가지를 마지막까지 기억해 주세요. 특히 3 번 '시계열 분할' 과 4 번 " +
    "'feature engineering 의 위력' 은 실제 우리 프로젝트의 P0 / P1 sprint 에서 증명된 사례입니다.\n\n" +
    "Keep these 5 goals in mind. Points 3 (time-ordered split) and 4 (feature engineering power) " +
    "were proven in our actual P0 / P1 sprints."
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
    "데이터는 항상 같은 흐름입니다 — 센서(측정) → 숫자(digitize) → 저장(storage) → 모델(model). " +
    "의료나 항공이나 본질은 같습니다. 이 4 단계를 계속 머릿속에 두세요."
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
    "이 네 가지 특성이 왜 '아무 데이터나 쓰면 안 되는가' 를 설명합니다. " +
    "실시간 · 고빈도 → Kafka 가 필요. 시계열 → shuffle 금지 (슬라이드 17). 다중 소스 → Schema Registry 필요 (슬라이드 11)."
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
    "4 개 소스 중 3 번 FAA SWIM 이 가장 도전적이었고 가장 자랑스러운 성과입니다. " +
    "나머지는 쉽게 접근 가능한 공개 데이터지만 SWIM 은 공식 구독 + TLS 인증서 + AIXM XML 파서가 모두 필요합니다."
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
  // 비행기 → 방송 → 수신기 → OpenSky → 우리
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
    "ADS-B 는 자동차의 블랙박스처럼 비행기가 스스로 자기 위치를 방송하는 시스템입니다. " +
    "방송 → 땅의 수신기가 받음 → OpenSky 서버가 집계 → 우리가 API 로 받음. " +
    "항공기 한 대당 17 개 필드가 10 초마다 들어옵니다."
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
    "METAR 는 항공 기상의 국제 표준 포맷입니다. 겉보기엔 암호 같지만 토큰 하나하나가 정확한 의미를 가집니다. " +
    "우리 코드는 이걸 파싱해서 JSON → Avro 로 변환해 Kafka 에 publish 합니다."
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
    "대학 캡스톤으로는 드물게 FAA 프로덕션 브로커에 직접 연결했습니다. " +
    "219 건을 60 초 안에 파싱 에러 0 으로 받은 로그가 증거입니다. " +
    "이게 가능했던 이유는 trust store 설정을 포기하지 않고 세 번 다시 했기 때문입니다."
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
    "EDA (Exploratory Data Analysis) 단계에서 가장 중요한 발견: 지연의 40% 가 '전편 지연' 에서 온다는 것. " +
    "이게 P1 sprint 에서 rotation features 5 개를 추가하게 된 도메인 근거가 되었고, Test R² 를 3.35 배 올려줬습니다."
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
    "같은 데이터를 JSON 으로 100 B, CSV 로 60 B, Avro 로 35 B 에 담습니다. " +
    "초당 수천 건 오는 Kafka 에서는 이 차이가 누적되어 거대합니다. 그리고 무엇보다 Avro 는 스키마를 강제하기 때문에 장애가 줄어듭니다."
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
    "Schema Registry 는 'producer 가 스키마를 바꿀 때 consumer 를 깨지 않도록' 강제하는 중앙 규칙 서버입니다. " +
    "BACKWARD 호환 정책은 '새 consumer 가 옛 데이터도 읽을 수 있어야 한다' 는 뜻입니다. " +
    "덕분에 장애 시 롤백이 안전합니다."
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
    "이 6 단계가 모든 ML 프로젝트의 기초입니다. 각 단계를 뛰어넘으면 반드시 나중에 문제가 생깁니다. " +
    "다음 슬라이드부터 각 단계를 하나씩 자세히 설명드리겠습니다."
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
    "진짜 원본 데이터는 이렇게 지저분합니다. 'null', '-9999', 음수 거리 같은 sentinel 값, 중복 레코드 등. " +
    "이걸 모르고 바로 모델 학습 시키면 쓰레기 입력 → 쓰레기 출력 (GIGO) 이 됩니다."
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

  // 우리가 선택한 것
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 5.1, w: 8.9, h: 0, fill: { color: C.navy }, line: { color: C.navy, width: 0 },
  });
  s.addText([
    { text: "💡 우리 프로젝트: ", options: { bold: true, color: C.amber, fontSize: 11 } },
    { text: "전처리 파이프라인에 SimpleImputer 를 넣고, 최종 모델은 XGBoost 라 native handling 도 동시에 작동", options: { color: C.white, fontSize: 10 } },
  ], {
    x: 0.5, y: 4.68, w: 8.9, h: 0.35, fill: { color: C.navy }, fontFace: FONT_B, margin: 0,
    valign: "middle",
  });

  addFooter(s, 14);
  s.addNotes(
    "XGBoost 가 인기 있는 이유 중 하나가 이겁니다 — 결측값을 그냥 받아줍니다. " +
    "다른 모델 (logistic regression, kNN 등) 은 NaN 이 있으면 아예 학습이 안 됩니다. " +
    "실무에서 이 편의성은 엄청난 시간 절약입니다."
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
    "가장 기본적인 feature engineering: 시간 분해. " +
    "모델은 '2026-04-19 14:30' 이라는 문자열을 아예 읽지 못합니다. " +
    "hour=14, month=4, is_weekend=1 처럼 숫자로 나눠줘야 XGBoost 가 패턴을 찾습니다."
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
    "이 슬라이드가 이 발표에서 가장 중요한 교훈입니다. '모델을 더 크게' 가 아니라 '도메인 지식을 feature 로' 가 정답이었다는 것. " +
    "같은 XGBoost 에 피처 5 개만 더했을 뿐인데 Test R² 가 0.10 에서 0.43 으로 3.35 배 올랐습니다."
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
    "초심자가 가장 많이 하는 실수입니다. sklearn 의 train_test_split 은 기본값이 shuffle=True 라서 " +
    "시계열 데이터에 그대로 쓰면 미래 정보가 과거 학습에 새어들어가 성능이 인위적으로 좋아 보입니다. " +
    "ADR-004 에 이걸 원칙으로 못박고 전체 파이프라인을 수정했습니다."
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
    "Bronze 가 있어서 원본을 재해석할 수 있고, Silver 가 있어서 여러 모델이 같은 feature 를 공유하고, " +
    "Gold 는 모델 소비 + 감사 추적용입니다. 사고 분석 시 '어느 레이어에서 틀어졌나' 를 layer-by-layer 로 추적 가능합니다."
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
    "같은 데이터 셋으로 만들 수 있는 프로젝트가 8 가지 이상 있습니다. " +
    "우리는 이 중 2 개 — 지연 예측과 이상 탐지 — 를 선택했습니다. 왜? " +
    "둘 다 관제사의 실제 의사결정에 직접 기여하기 때문입니다."
  );
}

// ─────────────────────────────────────────────────────────────────
// 슬라이드 20 · 우리가 만든 것
// ─────────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  addHeader(s, "CHAPTER 06 · OUR PROJECT", "우리가 만든 것", "What WE built — three integrated features");

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
    "우리가 만든 3 가지 기능. 각각 다른 데이터를 쓰는 것 같지만 공통 파이프라인에서 흘러나옵니다. " +
    "지연 예측은 Gold silver_flight_features, 이상 탐지는 Silver aircraft_phase, RAG 는 ChromaDB 161 chunks."
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
    "XGBoost 는 2014 년 Tianqi Chen 이 발표한 이후 Kaggle 우승 모델의 사실상 표준입니다. " +
    "4 가지 이유 중 가장 실무에서 중요한 것은 3 번 '해석성' — 관제사에게 '왜 이 예측인가' 를 SHAP 으로 설명할 수 있기 때문입니다."
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
    "Gradient Boosting 의 핵심 비유: 시험 공부할 때 '틀린 문제만 다시 보는 것' 과 같습니다. " +
    "첫 모델이 틀린 부분을 다음 모델이 집중 학습 → 그 다음 모델이 또 남은 오차를 학습 → 계속 개선. " +
    "200 개 트리의 합으로 강력한 앙상블이 됩니다."
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
    "세 개의 bar 가 모두 0.10 이고 마지막 두 개가 0.43 으로 뛰는 걸 보여주는 이유는 — " +
    "TimeSeriesSplit (P0) 자체로는 수치가 안 올라갔다는 걸 보여주기 위해서입니다. " +
    "진짜 향상은 P1 의 Rotation features 5 개가 만들었습니다."
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
    "항공 사고는 희귀해서 '정상 vs 사고' 라벨이 거의 없습니다. 이 상황에서 Autoencoder 를 쓰면 GPU 필요 + 학습 불안정. " +
    "Isolation Forest 는 이 두 문제를 모두 해결합니다 — 라벨 불필요 + CPU 분 단위 학습 + 해석 가능."
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
    "단계별 모델은 7 배의 운영 비용이 들지만, alert fatigue 67% 감소라는 구체적 성과로 정당화됩니다. " +
    "각 phase 마다 contamination (이상 예상률) 을 도메인 지식으로 튜닝했습니다 — TAXI 는 조용한 구간이라 0.02, LANDING 은 사고 빈발 구간이라 0.06."
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
    "Conformal Prediction 은 수학적으로 '90% 확률로 이 구간에 실제 값이 있다' 를 보장합니다. " +
    "분포 가정 없음 (distribution-free). MAPIE 라이브러리로 구현. 실측 coverage 가 정확히 90.00% 나온 것이 증거."
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
    "처음 ADS-B 전파부터 관제사 화면에 알림이 뜨기까지 전체 7 단계, p95 5 초 이내에 끝납니다. " +
    "각 단계의 지연: Kafka 100ms, Iceberg 조회 500ms, XGBoost 42ms, Conformal 100ms, LLM 2-3s, 나머지 network."
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
    "이 5 가지가 여러분이 이 발표에서 가져가야 할 전부입니다. " +
    "특히 2 번과 3 번은 실무에서 가장 많이 실수하는 부분이고, 우리 프로젝트의 P0/P1 sprint 가 그 증거입니다."
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
    "예상 질문 5 개. 답변 요약: " +
    "① Iceberg = ACID + schema evolution + time-travel. plain parquet 에는 없음. " +
    "② Bayesian 은 prior 가정 필요, Conformal 은 분포 가정 없음. " +
    "③ 단일 모델은 contamination 을 균일하게 써야 해서 phase 별 3배 차이를 반영 못함. " +
    "④ 10% sampling 은 chronological 하게 뽑아서 시간 편향 없게 했음. " +
    "⑤ 161 chunks 는 RAGAs 평가에서 faithfulness 0.91 · context_precision 0.85 로 충분 검증됨."
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
    "질문 받겠습니다. 감사합니다.\n\nThank you. Questions?"
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
