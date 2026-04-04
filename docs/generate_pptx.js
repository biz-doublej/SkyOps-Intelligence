const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "정재원";
pres.title = "SkyOps Intelligence — 최종 발표";

// Color palette
const BG = "0F172A";
const BG2 = "1E293B";
const BG3 = "334155";
const WHITE = "F1F5F9";
const MUTED = "94A3B8";
const ACCENT = "38BDF8";
const AMBER = "FBBF24";
const RED = "EF4444";
const GREEN = "22C55E";
const PURPLE = "A78BFA";

// Helper: add slide with dark bg + title
function mkSlide(title, subtitle) {
  const s = pres.addSlide();
  s.background = { color: BG };
  if (title) {
    s.addText(title, { x: 0.6, y: 0.3, w: 8.8, h: 0.6, fontSize: 32, fontFace: "Arial Black", color: WHITE, bold: true, margin: 0 });
  }
  if (subtitle) {
    s.addText(subtitle, { x: 0.6, y: 0.9, w: 8.8, h: 0.35, fontSize: 13, color: MUTED, margin: 0 });
  }
  // Bottom bar
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.35, w: 10, h: 0.275, fill: { color: ACCENT, transparency: 85 } });
  return s;
}

// Helper: card box
function card(s, x, y, w, h, opts = {}) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: opts.fill || BG2 } });
}

// Helper: stat callout
function stat(s, x, y, value, label, color = ACCENT) {
  card(s, x, y, 2.0, 1.1);
  s.addText(value, { x, y: y + 0.1, w: 2.0, h: 0.55, fontSize: 28, fontFace: "Arial Black", color, bold: true, align: "center", margin: 0 });
  s.addText(label, { x, y: y + 0.65, w: 2.0, h: 0.35, fontSize: 10, color: MUTED, align: "center", margin: 0 });
}

// ─── Slide 1: Title ───
const s1 = pres.addSlide();
s1.background = { color: BG };
s1.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: BG } });
s1.addShape(pres.shapes.RECTANGLE, { x: 0, y: 4.8, w: 10, h: 0.825, fill: { color: ACCENT, transparency: 85 } });
s1.addText("✈", { x: 4.0, y: 0.8, w: 2, h: 1.2, fontSize: 60, align: "center", color: ACCENT });
s1.addText("SkyOps Intelligence", { x: 0.5, y: 1.9, w: 9, h: 0.9, fontSize: 44, fontFace: "Arial Black", color: WHITE, bold: true, align: "center" });
s1.addText("실시간 항공 운항 이상 탐지 및 AI 관제 보조 플랫폼", { x: 0.5, y: 2.8, w: 9, h: 0.5, fontSize: 18, color: ACCENT, align: "center" });
s1.addText("2026학년도 1학기 캡스톤디자인  |  DoubleJ팀  |  정재원  |  지도교수: 조상구", { x: 0.5, y: 3.6, w: 9, h: 0.4, fontSize: 12, color: MUTED, align: "center" });

// ─── Slide 2: 문제 정의 ───
const s2 = mkSlide("문제 정의", "항공 산업이 직면한 핵심 과제");
const problems = [
  { icon: "💰", title: "연간 330억 달러 손실", desc: "FAA 기준 항공편 지연으로 인한\n경제적 손실 (전 세계)" },
  { icon: "⏱", title: "배치 기반 시스템 한계", desc: "사후 분석 중심으로\n실시간 대응 불가능" },
  { icon: "🔇", title: "도메인 LLM 부재", desc: "ATC 전문 용어/절차에\n특화된 AI 어시스턴트 없음" },
  { icon: "📊", title: "수동 이상 탐지", desc: "관제사 육안 모니터링 의존\n자동 감지 시스템 부재" },
];
problems.forEach((p, i) => {
  const cx = 0.5 + i * 2.3;
  card(s2, cx, 1.5, 2.1, 2.8);
  s2.addText(p.icon, { x: cx, y: 1.7, w: 2.1, h: 0.6, fontSize: 30, align: "center" });
  s2.addText(p.title, { x: cx + 0.15, y: 2.35, w: 1.8, h: 0.45, fontSize: 12, color: ACCENT, bold: true, align: "center", margin: 0 });
  s2.addText(p.desc, { x: cx + 0.15, y: 2.85, w: 1.8, h: 1.0, fontSize: 10, color: MUTED, align: "center", margin: 0 });
});

// ─── Slide 3: 솔루션 개요 ───
const s3 = mkSlide("솔루션 개요", "5-Layer 아키텍처");
const layers = [
  { label: "Layer 1", desc: "데이터 수집", tech: "OpenSky · METAR · Kaggle", color: ACCENT },
  { label: "Layer 2", desc: "스트리밍 처리", tech: "Kafka · Flink · Redis", color: "0EA5E9" },
  { label: "Layer 3", desc: "AI 모델", tech: "XGBoost · IF · LLM · RAG", color: PURPLE },
  { label: "Layer 4", desc: "API 서빙", tech: "FastAPI · vLLM · WebSocket", color: AMBER },
  { label: "Layer 5", desc: "대시보드", tech: "Next.js · Leaflet · MapLibre", color: GREEN },
];
layers.forEach((l, i) => {
  const cy = 1.5 + i * 0.75;
  s3.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: cy, w: 1.5, h: 0.55, rectRadius: 0.06, fill: { color: l.color, transparency: 20 } });
  s3.addText(l.label, { x: 0.6, y: cy, w: 1.5, h: 0.55, fontSize: 11, color: l.color, bold: true, align: "center", valign: "middle", margin: 0 });
  s3.addText(l.desc, { x: 2.3, y: cy, w: 2.5, h: 0.55, fontSize: 14, color: WHITE, bold: true, valign: "middle", margin: 0 });
  s3.addText(l.tech, { x: 5.0, y: cy, w: 4.5, h: 0.55, fontSize: 11, color: MUTED, valign: "middle", margin: 0 });
  if (i < 4) {
    s3.addText("↓", { x: 1.0, y: cy + 0.5, w: 0.7, h: 0.3, fontSize: 14, color: BG3, align: "center", margin: 0 });
  }
});

// ─── Slide 4: 데이터 수집 ───
const s4 = mkSlide("데이터 수집 (Layer 1)", "실시간 + 배치 데이터 통합");
stat(s4, 0.5, 1.5, "60~80", "대/30초 (한국 영공)");
stat(s4, 2.7, 1.5, "13,969", "Kaggle 학습 데이터");
stat(s4, 4.9, 1.5, "95K", "LLM 학습 데이터");
stat(s4, 7.1, 1.5, "30초", "폴링 주기");
card(s4, 0.5, 3.0, 8.8, 1.8);
s4.addText([
  { text: "• OpenSky ADS-B API — 전 세계 30,000+ 수신기 기반 실시간 항공기 위치", options: { breakLine: true, fontSize: 11, color: WHITE } },
  { text: "• NOAA METAR/TAF — 공항별 기상 데이터 (풍속, 시정, 운고)", options: { breakLine: true, fontSize: 11, color: WHITE } },
  { text: "• Kaggle Flight Delay Dataset — 미국 국내선 13,969건 (Feature Engineering 기반)", options: { breakLine: true, fontSize: 11, color: WHITE } },
  { text: "• LiveATC.net STT (Whisper large-v3) — ATC 교신 10시간 녹취 변환", options: { fontSize: 11, color: WHITE } },
], { x: 0.8, y: 3.15, w: 8.2, h: 1.5, valign: "top", margin: 0 });

// ─── Slide 5: 스트리밍 ───
const s5 = mkSlide("스트리밍 파이프라인 (Layer 2)", "Apache Kafka + PyFlink + Redis");
stat(s5, 0.5, 1.5, "3×3", "토픽 × 파티션");
stat(s5, 2.7, 1.5, "5분", "슬라이딩 윈도우");
stat(s5, 4.9, 1.5, "600s", "Redis TTL");
stat(s5, 7.1, 1.5, "3종", "CEP 이상 룰", AMBER);
card(s5, 0.5, 3.0, 8.8, 1.8);
s5.addText([
  { text: "Kafka Topics: flight-position, weather-event, gate-event", options: { breakLine: true, fontSize: 11, color: ACCENT } },
  { text: "PyFlink: 5분 윈도우 집계 (avg/min/max 고도, 속도, 수직속도)", options: { breakLine: true, fontSize: 11, color: WHITE } },
  { text: "Redis: ZSET(항공기 인덱스) + HASH(상태) + LIST(이상 이벤트)", options: { breakLine: true, fontSize: 11, color: WHITE } },
  { text: "CEP: ALTITUDE_SPIKE(152m/30s), VELOCITY_SPIKE, PATH_DEVIATION", options: { fontSize: 11, color: AMBER } },
], { x: 0.8, y: 3.15, w: 8.2, h: 1.5, valign: "top", margin: 0 });

// ─── Slide 6: Feature Engineering ───
const s6 = mkSlide("Feature Engineering", "20개 수치형 + 3개 범주형 = 23개 Feature");
const fgroups = [
  { name: "시간", features: "dep_hour, dep_dayofweek,\ndep_month, dep_dayofyear, is_weekend", color: ACCENT },
  { name: "노선", features: "distance_miles,\nsched_elapsed_min", color: "0EA5E9" },
  { name: "이력", features: "prev_dep_delay, prev_arr_delay,\nis_prev_delayed, carrier/route_hist", color: PURPLE },
  { name: "혼잡", features: "origin_hourly_departures,\ndest_hourly_arrivals", color: AMBER },
  { name: "기상", features: "weather_score,\norigin/dest_weather_hist_delay", color: GREEN },
];
fgroups.forEach((g, i) => {
  const cx = 0.3 + i * 1.92;
  card(s6, cx, 1.5, 1.75, 2.5);
  s6.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: cx + 0.25, y: 1.65, w: 1.25, h: 0.4, rectRadius: 0.06, fill: { color: g.color, transparency: 30 } });
  s6.addText(g.name, { x: cx + 0.25, y: 1.65, w: 1.25, h: 0.4, fontSize: 12, color: g.color, bold: true, align: "center", valign: "middle", margin: 0 });
  s6.addText(g.features, { x: cx + 0.1, y: 2.2, w: 1.55, h: 1.5, fontSize: 9, color: MUTED, align: "center", margin: 0 });
});

// ─── Slide 7: XGBoost ───
const s7 = mkSlide("XGBoost 지연 예측", "Optuna 하이퍼파라미터 최적화 + 5-Fold CV");
// Table
const tableRows = [
  [{ text: "모델", options: { bold: true, color: WHITE, fill: { color: BG3 } } }, { text: "RMSE", options: { bold: true, color: WHITE, fill: { color: BG3 } } }, { text: "MAE", options: { bold: true, color: WHITE, fill: { color: BG3 } } }, { text: "정확도", options: { bold: true, color: WHITE, fill: { color: BG3 } } }],
  [{ text: "DummyMean" }, { text: "27.13분" }, { text: "17.52분" }, { text: "88.8%" }],
  [{ text: "LinearRegression" }, { text: "25.34분" }, { text: "11.49분" }, { text: "87.8%" }],
  [{ text: "RandomForest" }, { text: "24.69분" }, { text: "11.29분" }, { text: "88.2%" }],
  [{ text: "XGBoost+Optuna ✅", options: { bold: true, color: ACCENT } }, { text: "24.64분", options: { bold: true, color: ACCENT } }, { text: "11.50분", options: { bold: true, color: ACCENT } }, { text: "88.3%", options: { bold: true, color: ACCENT } }],
];
s7.addTable(tableRows, { x: 0.5, y: 1.5, w: 9, fontSize: 11, color: WHITE, border: { type: "solid", pt: 0.5, color: BG3 }, rowH: 0.4, colW: [3, 2, 2, 2], fill: { color: BG2 } });
stat(s7, 0.5, 3.8, "10.4초", "학습 시간", GREEN);
stat(s7, 2.7, 3.8, "88.3%", "분류 정확도", ACCENT);
stat(s7, 4.9, 3.8, "0.090", "R² Score", AMBER);

// ─── Slide 8: SHAP ───
const s8 = mkSlide("SHAP Feature Importance", "XGBoost 예측 해석 — 상위 5 Feature");
const shapFeatures = [
  { name: "dep_dayofyear (연중일)", val: "5.702", pct: 90 },
  { name: "prev_arr_delay (직전편 지연)", val: "2.930", pct: 47 },
  { name: "route_hist_delay (노선 이력)", val: "2.401", pct: 38 },
  { name: "dep_hour (출발 시간)", val: "1.871", pct: 30 },
  { name: "carrier_hist_delay (항공사)", val: "0.869", pct: 14 },
];
shapFeatures.forEach((f, i) => {
  const cy = 1.5 + i * 0.7;
  s8.addText(f.name, { x: 0.6, y: cy, w: 3.5, h: 0.4, fontSize: 11, color: WHITE, valign: "middle", margin: 0 });
  s8.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 4.3, y: cy + 0.05, w: f.pct * 0.045, h: 0.3, rectRadius: 0.04, fill: { color: ACCENT } });
  s8.addText(f.val + "분", { x: 4.3 + f.pct * 0.045 + 0.1, y: cy, w: 1.5, h: 0.4, fontSize: 11, color: ACCENT, bold: true, valign: "middle", margin: 0 });
});
card(s8, 0.5, 4.2, 9, 0.9);
s8.addText("핵심 인사이트: Cascade Delay — 직전편 지연이 체인처럼 전파 (prev_arr + prev_dep = 3.26분)", { x: 0.8, y: 4.35, w: 8.5, h: 0.6, fontSize: 11, color: AMBER, margin: 0 });

// ─── Slide 9: IF + CEP ───
const s9 = mkSlide("이상 탐지", "Isolation Forest + CEP 룰 엔진 앙상블");
stat(s9, 0.5, 1.5, "0.335", "IF F1 Score", RED);
stat(s9, 2.7, 1.5, "0.359", "Precision", AMBER);
stat(s9, 4.9, 1.5, "0.314", "Recall", AMBER);
stat(s9, 7.1, 1.5, "3종", "CEP 룰", GREEN);
card(s9, 0.5, 3.0, 8.8, 2.0);
s9.addText([
  { text: "CEP 룰 엔진 (실시간 ADS-B 스트림)", options: { breakLine: true, fontSize: 12, color: ACCENT, bold: true } },
  { text: "• ALTITUDE_SPIKE: 고도 급변 > 152m/30초 (FAA AIM 기준 500ft/분)", options: { breakLine: true, fontSize: 10, color: WHITE } },
  { text: "• VELOCITY_SPIKE: 속도 이상 > 50m/s/30초", options: { breakLine: true, fontSize: 10, color: WHITE } },
  { text: "• PATH_DEVIATION: 경로 이탈 > 5km", options: { breakLine: true, fontSize: 10, color: WHITE } },
  { text: "• 심각도 3단계: LOW(1~1.5배) / MEDIUM(1.5~2배) / HIGH(2배+)", options: { fontSize: 10, color: AMBER } },
], { x: 0.8, y: 3.15, w: 8.2, h: 1.7, valign: "top", margin: 0 });

// ─── Slide 10: LLM 데이터 ───
const s10 = mkSlide("LLM 학습 데이터 구축", "항공 도메인 특화 95K건 데이터셋");
stat(s10, 0.5, 1.5, "60K", "GPT-4 QA 생성", ACCENT);
stat(s10, 2.7, 1.5, "10K", "이상 탐지 설명", AMBER);
stat(s10, 4.9, 1.5, "5K", "승객 안내문", GREEN);
stat(s10, 7.1, 1.5, "10h", "ATC 교신 STT", PURPLE);
card(s10, 0.5, 3.0, 8.8, 1.8);
s10.addText([
  { text: "데이터 파이프라인", options: { breakLine: true, fontSize: 12, color: ACCENT, bold: true } },
  { text: "1. LiveATC.net 공개 녹취 → Whisper large-v3 STT 변환", options: { breakLine: true, fontSize: 10, color: WHITE } },
  { text: "2. ICAO 문서 PDF 파싱 (AIM, FAR Part 91/121)", options: { breakLine: true, fontSize: 10, color: WHITE } },
  { text: "3. GPT-4 API로 Instruction-Input-Output QA 쌍 자동 생성", options: { breakLine: true, fontSize: 10, color: WHITE } },
  { text: "4. Alpaca 포맷 전처리 → 최종 데이터셋 저장", options: { fontSize: 10, color: WHITE } },
], { x: 0.8, y: 3.15, w: 8.2, h: 1.5, valign: "top", margin: 0 });

// ─── Slide 11: QLoRA ───
const s11 = mkSlide("QLoRA 파인튜닝", "Qwen2.5-7B-Instruct · 4-bit NF4 · RTX 3070 8GB");
stat(s11, 0.5, 1.5, "0.1053", "Train Loss", ACCENT);
stat(s11, 2.7, 1.5, "97.88%", "Token Accuracy", GREEN);
stat(s11, 4.9, 1.5, "9시간", "학습 시간", AMBER);
stat(s11, 7.1, 1.5, "0.92%", "학습 파라미터 비율", PURPLE);
card(s11, 0.5, 3.0, 4.2, 1.8);
s11.addText([
  { text: "학습 설정", options: { breakLine: true, fontSize: 12, color: ACCENT, bold: true } },
  { text: "LoRA rank: 64 / alpha: 16", options: { breakLine: true, fontSize: 10, color: WHITE } },
  { text: "Batch size: 1 (grad_accum: 16)", options: { breakLine: true, fontSize: 10, color: WHITE } },
  { text: "Learning rate: 2e-4", options: { breakLine: true, fontSize: 10, color: WHITE } },
  { text: "Epochs: 2 / Steps: 1,594", options: { fontSize: 10, color: WHITE } },
], { x: 0.7, y: 3.15, w: 3.8, h: 1.5, valign: "top", margin: 0 });
card(s11, 5.1, 3.0, 4.2, 1.8);
s11.addText([
  { text: "결과", options: { breakLine: true, fontSize: 12, color: GREEN, bold: true } },
  { text: "Eval Loss: 0.0445", options: { breakLine: true, fontSize: 10, color: WHITE } },
  { text: "Trainable Params: 40.4M / 4.4B", options: { breakLine: true, fontSize: 10, color: WHITE } },
  { text: "Adapter Size: 155 MB", options: { breakLine: true, fontSize: 10, color: WHITE } },
  { text: "Samples/sec: 0.787", options: { fontSize: 10, color: WHITE } },
], { x: 5.3, y: 3.15, w: 3.8, h: 1.5, valign: "top", margin: 0 });

// ─── Slide 12: DPO ───
const s12 = mkSlide("DPO 선호도 정렬", "Direct Preference Optimization · 12시간 학습");
stat(s12, 0.5, 1.5, "100%", "Rewards Accuracy", GREEN);
stat(s12, 2.7, 1.5, "0.0294", "Eval Loss", ACCENT);
stat(s12, 4.9, 1.5, "8.91", "Margins (최종)", AMBER);
stat(s12, 7.1, 1.5, "34%↓", "SFT 대비 개선", GREEN);
card(s12, 0.5, 3.0, 8.8, 1.8);
s12.addText([
  { text: "DPO 핵심 결과", options: { breakLine: true, fontSize: 12, color: ACCENT, bold: true } },
  { text: "• Step 20부터 chosen > rejected 100% 판별 성공", options: { breakLine: true, fontSize: 10, color: WHITE } },
  { text: "• Rewards Margins: 0.80 → 8.91 (선호도 격차 지속 확대)", options: { breakLine: true, fontSize: 10, color: WHITE } },
  { text: "• Eval Loss: SFT(0.0445) → DPO(0.0294) — 34% 개선", options: { breakLine: true, fontSize: 10, color: GREEN } },
  { text: "• 총 119 Steps / 1 Epoch / beta=0.1", options: { fontSize: 10, color: MUTED } },
], { x: 0.8, y: 3.15, w: 8.2, h: 1.5, valign: "top", margin: 0 });

// ─── Slide 13: 벤치마크 ───
const s13 = mkSlide("도메인 벤치마크 평가", "500건 평가셋 · ROUGE-L / BLEU");
const benchRows = [
  [{ text: "유형", options: { bold: true, color: WHITE, fill: { color: BG3 } } }, { text: "n", options: { bold: true, color: WHITE, fill: { color: BG3 } } }, { text: "ROUGE-L", options: { bold: true, color: WHITE, fill: { color: BG3 } } }, { text: "BLEU-1", options: { bold: true, color: WHITE, fill: { color: BG3 } } }],
  [{ text: "전체", options: { bold: true } }, { text: "500" }, { text: "0.169", options: { bold: true, color: ACCENT } }, { text: "0.121", options: { bold: true, color: ACCENT } }],
  [{ text: "이상 탐지 설명" }, { text: "331" }, { text: "0.159" }, { text: "0.111" }],
  [{ text: "승객 안내문" }, { text: "125" }, { text: "0.225", options: { color: GREEN } }, { text: "0.170", options: { color: GREEN } }],
  [{ text: "규정 QA" }, { text: "44" }, { text: "0.090", options: { color: RED } }, { text: "0.064", options: { color: RED } }],
];
s13.addTable(benchRows, { x: 0.5, y: 1.5, w: 9, fontSize: 11, color: WHITE, border: { type: "solid", pt: 0.5, color: BG3 }, rowH: 0.45, fill: { color: BG2 } });
card(s13, 0.5, 3.8, 8.8, 1.2);
s13.addText("해석: 생성형 LLM은 동일 의미를 다른 어휘로 표현해도 BLEU/ROUGE가 낮게 측정됨.\n승객 안내문(ROUGE 0.225)은 정형화된 문체 학습 효과 확인. 규정 QA(0.090)는 학습 데이터 부족.", { x: 0.8, y: 3.9, w: 8.2, h: 1.0, fontSize: 10, color: MUTED, margin: 0 });

// ─── Slide 14: MLOps ───
const s14 = mkSlide("MLOps 파이프라인", "자동 재학습 + 드리프트 감지 + 모니터링");
const mlops = [
  { title: "MLflow", desc: "실험 추적\n파라미터·메트릭 자동 로깅\n모델 버전 관리", color: ACCENT },
  { title: "Airflow", desc: "일 1회 재학습 DAG\n데이터 신선도 체크\n조건부 재학습 트리거", color: AMBER },
  { title: "EvidentlyAI", desc: "Feature 분포 드리프트 감지\nJensen-Shannon 발산\n키워드 빈도 모니터링", color: PURPLE },
  { title: "Slack", desc: "Webhook 알림\n재학습 결과 통보\n이상 감지 경고", color: GREEN },
];
mlops.forEach((m, i) => {
  const cx = 0.3 + i * 2.4;
  card(s14, cx, 1.5, 2.2, 3.0);
  s14.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: cx + 0.35, y: 1.7, w: 1.5, h: 0.4, rectRadius: 0.06, fill: { color: m.color, transparency: 30 } });
  s14.addText(m.title, { x: cx + 0.35, y: 1.7, w: 1.5, h: 0.4, fontSize: 12, color: m.color, bold: true, align: "center", valign: "middle", margin: 0 });
  s14.addText(m.desc, { x: cx + 0.2, y: 2.3, w: 1.8, h: 1.8, fontSize: 9, color: MUTED, align: "center", margin: 0 });
});

// ─── Slide 15: vLLM + RAG ───
const s15 = mkSlide("vLLM 서빙 + RAG", "AWQ 4-bit 양자화 · ChromaDB + LangChain");
stat(s15, 0.5, 1.5, "4-bit", "AWQ 양자화", ACCENT);
stat(s15, 2.7, 1.5, "47분", "양자화 시간", AMBER);
stat(s15, 4.9, 1.5, "5.2GB", "GPU 메모리", GREEN);
stat(s15, 7.1, 1.5, "5~13", "tok/s", PURPLE);
card(s15, 0.5, 3.0, 4.2, 1.8);
s15.addText([
  { text: "vLLM 서빙", options: { breakLine: true, fontSize: 12, color: ACCENT, bold: true } },
  { text: "• awq_marlin 커널 (최적화)", options: { breakLine: true, fontSize: 10, color: WHITE } },
  { text: "• Max Model Len: 2,048", options: { breakLine: true, fontSize: 10, color: WHITE } },
  { text: "• KV Cache: 3,680 토큰", options: { breakLine: true, fontSize: 10, color: WHITE } },
  { text: "• OpenAI 호환 API", options: { fontSize: 10, color: WHITE } },
], { x: 0.7, y: 3.15, w: 3.8, h: 1.5, valign: "top", margin: 0 });
card(s15, 5.1, 3.0, 4.2, 1.8);
s15.addText([
  { text: "RAG 체인", options: { breakLine: true, fontSize: 12, color: GREEN, bold: true } },
  { text: "• ChromaDB 벡터 DB", options: { breakLine: true, fontSize: 10, color: WHITE } },
  { text: "• BAAI/bge-m3 임베딩 (CPU)", options: { breakLine: true, fontSize: 10, color: WHITE } },
  { text: "• LangChain LCEL 체인", options: { breakLine: true, fontSize: 10, color: WHITE } },
  { text: "• Top-K: 4 / Temp: 0.2", options: { fontSize: 10, color: WHITE } },
], { x: 5.3, y: 3.15, w: 3.8, h: 1.5, valign: "top", margin: 0 });

// ─── Slide 16: FastAPI ───
const s16 = mkSlide("FastAPI 서빙", "13개 엔드포인트 · REST + WebSocket + Prometheus");
stat(s16, 0.5, 1.5, "11ms", "지연 예측", GREEN);
stat(s16, 2.7, 1.5, "15ms", "이상 탐지", GREEN);
stat(s16, 4.9, 1.5, "~1초", "LLM 직접", AMBER);
stat(s16, 7.1, 1.5, "13개", "엔드포인트", ACCENT);
card(s16, 0.5, 3.0, 8.8, 2.0);
s16.addText([
  { text: "REST: /predict/delay, /detect/anomaly, /chat, /explain/anomaly, /generate/announcement", options: { breakLine: true, fontSize: 10, color: ACCENT } },
  { text: "REST: /aircraft/live, /aircraft/h3, /anomaly/recent, /health", options: { breakLine: true, fontSize: 10, color: WHITE } },
  { text: "WebSocket: /ws/aircraft (3초), /ws/anomalies (1초)", options: { breakLine: true, fontSize: 10, color: GREEN } },
  { text: "Prometheus: /metrics (요청 수, 레이턴시, 상태코드)", options: { breakLine: true, fontSize: 10, color: AMBER } },
  { text: "한국어 후처리: _clean_korean() — 중국어 코드스위칭 필터링", options: { fontSize: 10, color: MUTED } },
], { x: 0.8, y: 3.15, w: 8.2, h: 1.7, valign: "top", margin: 0 });

// ─── Slide 17: Dashboard ───
const s17 = mkSlide("Next.js 실시간 관제 대시보드", "6개 페이지 · 다크 테마 · WebSocket 실시간");
const pages = [
  { name: "대시보드", desc: "KPI 카드 4종\n알림 + 항공기 요약", icon: "📊" },
  { name: "실시간 지도", desc: "Leaflet 라이브맵\nWebSocket + SWR", icon: "🗺" },
  { name: "이상 탐지", desc: "실시간 피드\nAI 분석 버튼", icon: "🚨" },
  { name: "지연 예측", desc: "항공사/공항 폼\nXGBoost 결과", icon: "⏱" },
  { name: "혼잡도 맵", desc: "MapLibre GL\nH3 히트맵", icon: "🔥" },
  { name: "AI 챗봇", desc: "RAG 채팅\n안내문 생성", icon: "🤖" },
];
pages.forEach((p, i) => {
  const row = Math.floor(i / 3);
  const col = i % 3;
  const cx = 0.4 + col * 3.15;
  const cy = 1.5 + row * 1.9;
  card(s17, cx, cy, 2.95, 1.6);
  s17.addText(p.icon, { x: cx, y: cy + 0.1, w: 2.95, h: 0.4, fontSize: 22, align: "center", margin: 0 });
  s17.addText(p.name, { x: cx, y: cy + 0.55, w: 2.95, h: 0.35, fontSize: 12, color: ACCENT, bold: true, align: "center", margin: 0 });
  s17.addText(p.desc, { x: cx + 0.2, y: cy + 0.9, w: 2.55, h: 0.55, fontSize: 9, color: MUTED, align: "center", margin: 0 });
});

// ─── Slide 18: 시나리오 ───
const s18 = mkSlide("사용자 시나리오 3종", "실제 운영 상황 기반 데모");
const scenarios = [
  { num: "1", title: "기상 악화 → 지연 예측 → 안내문", desc: "인천공항 강풍 45노트 감지\n→ XGBoost +38분 지연 예측\n→ AI 승객 안내문 자동 생성", color: AMBER },
  { num: "2", title: "이상 비행 → LLM 설명 → 대응", desc: "KAL1133 고도 급변 427m/23초\n→ AI 원인 분석 (HIGH)\n→ FAA AIM 기반 대응 절차", color: RED },
  { num: "3", title: "FAA 규정 QA", desc: "관제사: '비상 선언 항공기\n7700 Squawk 대응 절차는?'\n→ RAG 검색 + LLM 답변", color: ACCENT },
];
scenarios.forEach((sc, i) => {
  const cx = 0.3 + i * 3.2;
  card(s18, cx, 1.5, 3.0, 3.2);
  s18.addShape(pres.shapes.OVAL, { x: cx + 1.1, y: 1.7, w: 0.8, h: 0.8, fill: { color: sc.color, transparency: 30 } });
  s18.addText(sc.num, { x: cx + 1.1, y: 1.7, w: 0.8, h: 0.8, fontSize: 22, color: sc.color, bold: true, align: "center", valign: "middle", margin: 0 });
  s18.addText(sc.title, { x: cx + 0.15, y: 2.65, w: 2.7, h: 0.45, fontSize: 11, color: sc.color, bold: true, align: "center", margin: 0 });
  s18.addText(sc.desc, { x: cx + 0.15, y: 3.15, w: 2.7, h: 1.2, fontSize: 9, color: MUTED, align: "center", margin: 0 });
});

// ─── Slide 19: 성능 벤치마크 ───
const s19 = mkSlide("종합 성능 벤치마크", "목표 대비 달성 현황");
const perfRows = [
  [{ text: "구분", options: { bold: true, fill: { color: BG3 } } }, { text: "지표", options: { bold: true, fill: { color: BG3 } } }, { text: "목표", options: { bold: true, fill: { color: BG3 } } }, { text: "실측", options: { bold: true, fill: { color: BG3 } } }, { text: "", options: { bold: true, fill: { color: BG3 } } }],
  [{ text: "지연 예측" }, { text: "RMSE" }, { text: "≤15분" }, { text: "24.64분" }, { text: "△", options: { color: AMBER } }],
  [{ text: "지연 예측" }, { text: "분류 정확도" }, { text: "≥75%" }, { text: "88.3%", options: { color: GREEN } }, { text: "✅", options: { color: GREEN } }],
  [{ text: "이상 탐지" }, { text: "F1 Score" }, { text: "≥0.85" }, { text: "0.335", options: { color: RED } }, { text: "✗", options: { color: RED } }],
  [{ text: "LLM" }, { text: "Token Acc" }, { text: "—" }, { text: "97.88%", options: { color: GREEN } }, { text: "✅", options: { color: GREEN } }],
  [{ text: "DPO" }, { text: "Rewards Acc" }, { text: "—" }, { text: "100%", options: { color: GREEN } }, { text: "✅", options: { color: GREEN } }],
  [{ text: "API" }, { text: "지연 예측" }, { text: "≤500ms" }, { text: "11ms", options: { color: GREEN } }, { text: "✅", options: { color: GREEN } }],
];
s19.addTable(perfRows, { x: 0.5, y: 1.4, w: 9, fontSize: 11, color: WHITE, border: { type: "solid", pt: 0.5, color: BG3 }, rowH: 0.45, colW: [2, 2, 1.5, 2, 1.5], fill: { color: BG2 } });

// ─── Slide 20: 한계 & 개선 ───
const s20 = mkSlide("한계 및 개선 방향", "솔직한 분석 + 다음 단계");
const limits = [
  { issue: "RMSE 24.64분 (목표 15분)", cause: "미국 데이터, 기상 미반영", fix: "한국공항공사 ACDM API\n실시간 METAR Feature", color: AMBER },
  { issue: "IF F1 0.335", cause: "비지도 학습 한계", fix: "Autoencoder 전환\n반지도 학습 적용", color: RED },
  { issue: "LLM 중국어 혼합", cause: "Qwen2.5 기본 언어", fix: "한국어 특화 모델\n(SOLAR/KULLM)", color: PURPLE },
  { issue: "추론 5~13 tok/s", cause: "RTX 3070 8GB 제한", fix: "GPU 업그레이드 (A100)\nSpeculative Decoding", color: ACCENT },
];
limits.forEach((l, i) => {
  const cy = 1.4 + i * 0.95;
  s20.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: cy, w: 0.08, h: 0.75, fill: { color: l.color } });
  s20.addText(l.issue, { x: 0.8, y: cy, w: 2.5, h: 0.75, fontSize: 10, color: l.color, bold: true, valign: "middle", margin: 0 });
  s20.addText(l.cause, { x: 3.5, y: cy, w: 2.5, h: 0.75, fontSize: 10, color: MUTED, valign: "middle", margin: 0 });
  s20.addText(l.fix, { x: 6.2, y: cy, w: 3.3, h: 0.75, fontSize: 10, color: WHITE, valign: "middle", margin: 0 });
});
// Header labels
s20.addText("한계", { x: 0.8, y: 1.1, w: 2.5, h: 0.3, fontSize: 9, color: BG3, bold: true, margin: 0 });
s20.addText("원인", { x: 3.5, y: 1.1, w: 2.5, h: 0.3, fontSize: 9, color: BG3, bold: true, margin: 0 });
s20.addText("개선 방향", { x: 6.2, y: 1.1, w: 3.3, h: 0.3, fontSize: 9, color: BG3, bold: true, margin: 0 });

// ─── Slide 21: 결론 ───
const s21 = pres.addSlide();
s21.background = { color: BG };
s21.addText("결론 & 기대효과", { x: 0.5, y: 0.3, w: 9, h: 0.6, fontSize: 32, fontFace: "Arial Black", color: WHITE, bold: true, margin: 0 });
const conclusions = [
  { icon: "✅", text: "실시간 스트리밍 + ML + LLM + RAG + 대시보드\n엔드투엔드 AI 관제 보조 시스템 PoC 완성" },
  { icon: "🛡", text: "관제 안전성 향상\n이중 확인 체계 (AI 보조 + 관제사 판단)" },
  { icon: "⚡", text: "관제사 업무 경감\n안내문 5초 생성, SOP 즉시 검색, 이상 자동 설명" },
  { icon: "🎯", text: "ML/AI 엔지니어 포트폴리오\nKafka, vLLM, QLoRA, DPO, Next.js 풀스택" },
];
conclusions.forEach((c, i) => {
  const cy = 1.2 + i * 0.95;
  card(s21, 0.5, cy, 9, 0.8);
  s21.addText(c.icon, { x: 0.7, y: cy + 0.05, w: 0.7, h: 0.7, fontSize: 22, align: "center", valign: "middle", margin: 0 });
  s21.addText(c.text, { x: 1.5, y: cy + 0.05, w: 7.5, h: 0.7, fontSize: 11, color: WHITE, valign: "middle", margin: 0 });
});
s21.addText("감사합니다", { x: 0.5, y: 5.0, w: 9, h: 0.5, fontSize: 24, fontFace: "Arial Black", color: ACCENT, align: "center", margin: 0 });

// ─── Save ───
const outPath = process.argv[2] || "C:\\Users\\jaewo\\Desktop\\SkyOps Intelligence\\docs\\skyops_final_presentation.pptx";
pres.writeFile({ fileName: outPath }).then(() => {
  console.log("PPTX saved:", outPath);
}).catch(err => {
  console.error("Error:", err);
});
