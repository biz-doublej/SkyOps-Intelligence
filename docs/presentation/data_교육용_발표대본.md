# SkyOps Intelligence — 데이터 교육용 발표 대본
# Aviation Data Story — Educational Speaker Script

> **발표 시간 / Duration**: 25~30 분 · 30 슬라이드 · 슬라이드당 평균 50~60 초
> **청중 / Audience**: 빅데이터과 한국인 학생 + 교환학생 (Korean + international students, mixed background)
> **언어 정책 / Language policy**: 한국어 메인, 영어 핵심 용어를 괄호로 병기 · Korean main with English technical terms in parentheses
> **톤 / Tone**: 교육적 · 단계적 · 예시 중심 · educational, step-by-step, example-driven

---

## 📌 발표자 가이드 / Presenter Guide

- 각 슬라이드에 **한 번씩 "왜 이걸 썼는가"** 를 강조 · stress the "why" once per slide
- 외국인 학생을 위해 **영어 핵심 용어** 를 처음 등장 시 한 번씩 또렷이 발음 · pronounce English terms clearly
- 슬라이드 16 (Rotation +335%) 과 17 (TimeSeriesSplit) 은 **특히 천천히**, 학생들이 필기할 시간을 줌
- Q&A 에 대비해 슬라이드 29 의 답변 요약을 미리 숙지

---

## 슬라이드 1 · 표지 / Cover (30 초)

안녕하세요 (Hello). 빅데이터과 3학년 정재원입니다. 오늘은 저희 DoubleJ 팀이 만든 SkyOps Intelligence 프로젝트의 **데이터 (data)** 이야기를 해보려 합니다.

Today I'll focus on the **data side** of our SkyOps Intelligence project — how data is collected, transformed, and finally becomes a model.

앞으로 30 장 동안, 여러분은 다음 질문에 대한 답을 찾게 됩니다.

> "원본 데이터 한 줄이 어떻게 관제사 화면의 알림 하나가 되는가?"

By the end of this talk, you'll understand how **one row of raw data becomes one alert on an air traffic controller's screen**.

---

## 슬라이드 2 · 학습 목표 / Learning Objectives (30 초)

이 발표가 끝났을 때 여러분은 다음 5 가지를 알게 됩니다.

1. **항공 데이터가 어떻게 생성되는가** · How aviation data is generated
2. **raw 데이터를 어떻게 정제하는가** · How to clean raw data
3. **왜 시계열 분할이 중요한가** · Why time-ordered split matters (temporal leakage)
4. **Feature Engineering 이 모델을 어떻게 바꾸는가** — 실제 사례 R² +335% · Real case, 3.35× improvement
5. **XGBoost / Isolation Forest 가 왜 선택됐는가** · Why these models, not others

특히 3 번과 4 번이 가장 중요합니다. 이 두 가지는 실제로 저희 프로젝트의 P0, P1 스프린트에서 증명된 내용이라 숫자를 기억해 두세요.

Points **3 and 4 are the most important** — they were proven in our P0 / P1 sprints with real numbers.

---

## 슬라이드 3 · 데이터란 무엇인가? / What is Data? (50 초)

잠깐 기본으로 돌아가겠습니다. 데이터란 무엇일까요?

Let's step back to basics. What IS data?

**데이터는 세상의 측정값입니다 (Data = quantified observations of the world).**

슬라이드를 보시면 의료와 항공 두 예시가 있습니다.

의료에서는: 체온계 → 37.5°C → EHR 데이터베이스 → 진단 모델
In medicine: thermometer → 37.5°C → EHR DB → diagnostic model

항공에서는: 레이더 수신기 → 위도·경도 → Kafka 스트림 → 지연 예측
In aviation: radar receiver → lat/lon → Kafka stream → delay prediction

**이 4 단계 구조 — 센서, 숫자, 저장, 모델 — 는 어떤 도메인이든 동일합니다**. 이걸 머릿속에 두면 나머지 슬라이드가 전부 이 프레임에 맞아 들어갑니다.

These **4 steps — sensor, numeric, storage, model — are universal**. Keep this frame in your head; every slide from now on fits into it.

---

## 슬라이드 4 · 항공 데이터의 특성 / Aviation Data Characteristics (45 초)

항공 데이터는 4 가지 특별한 성질이 있습니다.

Aviation data has four special characteristics.

1. **실시간 (Real-time)** — 초 단위로 업데이트됩니다. 1 분 지연도 큰 의미가 있습니다.
2. **고빈도 (High frequency)** — 초당 수천 건이 들어옵니다.
3. **시계열 (Time-series)** — 순서 (order) 가 중요합니다. 10:00 먼저, 10:01 나중. 섞으면 안 됩니다.
4. **다중 소스 (Multi-source)** — 레이더 + 기상 + 관제 메시지가 다 합쳐져야 의미가 생깁니다.

**이 4 가지가 '아무 데이터나 아무 방식으로 쓰면 안 되는' 이유입니다.**

These four properties explain why you can't just throw aviation data into any ML pipeline:
- 실시간 + 고빈도 → Kafka 가 필요 (we need Kafka)
- 시계열 → **절대 shuffle 하지 마세요** (never shuffle — slide 17)
- 다중 소스 → Schema Registry 가 필요 (we need a contract — slide 11)

---

## 슬라이드 5 · 4개 데이터 소스 개요 / Four Data Sources (60 초)

저희는 총 4 가지 데이터 소스를 씁니다.

We use four data sources in total.

1. **OpenSky Network** — 전 세계 35,000 개 지상 수신기가 기여하는 공개 ADS-B 네트워크. 10 초마다 항공기 위치.
   *35,000 ground receivers worldwide, crowdsourced ADS-B, 10-second polling.*
2. **NOAA + KMA METAR** — 공항 기상 보고서. 30 분 주기.
   *Airport weather reports, 30-min update.*
3. **FAA SWIM ★** — 미 연방항공청 공식 System Wide Information Management. 이 별표가 붙은 이유는 잠시 후에.
   *US FAA production data stream, will explain the star shortly.*
4. **Kaggle flights.csv** — US DOT Bureau of Transportation Statistics 의 2015 년 배치 데이터. 5.7 M 행.
   *US DOT BTS 2015 batch dataset, 5.7M rows.*

별표가 붙은 SWIM 이 **이 프로젝트의 플래그십 성과**입니다. 왜 그런지 슬라이드 8 에서 자세히 보여드립니다.

The starred SWIM source is **our flagship achievement** — I'll show you why at slide 8.

---

## 슬라이드 6 · OpenSky ADS-B 작동 원리 / How ADS-B Works (60 초)

ADS-B 가 뭔지 모르는 학생들을 위해 짧게 설명드립니다.

For those unfamiliar with ADS-B — a quick explanation.

**ADS-B = Automatic Dependent Surveillance-Broadcast**

슬라이드에 흐름이 나와있습니다.

1. **항공기 (aircraft)** 가 자기 위치를 스스로 방송합니다. 마치 자동차 블랙박스 같은 장치가 계속 "나 여기 있어요" 라고 외치는 것.
2. **지상 수신기 (ground receiver)** 가 이 신호를 받습니다. 전 세계 35,000 대가 있고, 대부분 자원봉사자가 운영합니다.
3. 수신기들이 데이터를 **OpenSky 서버 (API)** 로 보냅니다.
4. 저희는 30 초마다 OpenSky API 를 폴링 해서 **Kafka 의 flight-position 토픽** 으로 publish 합니다.

**한 편의 항공기에서 17 개 필드가 들어옵니다.** 슬라이드 하단에 9 개만 뽑아 보여드렸습니다 — icao24 (항공기 고유 ID), callsign, lat/lon, altitude, velocity, 등.

Each aircraft sends **17 fields per update**. The bottom shows 9 key ones — unique ICAO24 hex ID, callsign, coordinates, altitude, and so on.

---

## 슬라이드 7 · METAR 해독 실습 / Decoding a METAR (60 초)

두 번째 소스는 METAR 기상 보고서인데, 처음 보면 암호 같아서 함께 해독해 봅시다.

Our second source is METAR — it looks like code at first, so let's decode one together.

슬라이드 상단의 검은 박스를 보세요.

> `RKSI 030900Z 29012KT 9999 SCT030 08/M02 Q1020`

이 한 줄을 7 개 토큰으로 나눌 수 있습니다.

This single line decomposes into 7 tokens:

- **RKSI** = 인천국제공항 ICAO 코드 (Incheon Intl ICAO code)
- **030900Z** = 매월 3일 09:00 UTC 관측 (day-03 09:00 UTC)
- **29012KT** = 풍향 290°, 풍속 12 노트 (wind from 290°, 12 knots)
- **9999** = 가시거리 10 km 이상 (visibility ≥10 km)
- **SCT030** = 3,000 ft 에 구름 부분 있음 (scattered clouds at 3,000 ft)
- **08/M02** = 기온 8°C / 이슬점 -2°C (temp 8°C / dewpoint -2°C)
- **Q1020** = QNH 압력 1020 hPa (altimeter setting 1020 hPa)

**항공 표준** 이라서 전 세계가 이 한 가지 포맷을 씁니다. 저희 코드가 이걸 파싱해서 JSON 으로 만들고, 다시 Avro 로 바꿔 Kafka 에 넣습니다.

This is an **international aviation standard** — every airport worldwide uses it. Our parser turns it into JSON, then Avro, then pushes to Kafka.

---

## 슬라이드 8 · FAA SWIM 실연동 — 플래그십 성과 / FAA SWIM Live Integration (90 초)

자, 별표가 붙었던 소스입니다. 이 프로젝트에서 **가장 자랑스러운 성과**라 슬라이드 한 장을 통째로 썼습니다.

Here's the starred source. **The most proud moment** of this project, so the whole slide.

슬라이드 오른쪽 위에 주황 박스를 보시면 — "60 초 / 219 건 / parse_err = 0" 이렇게 적혀 있습니다. 이게 무슨 뜻이냐면:

> 미 연방항공청 (FAA) 의 프로덕션 브로커 에 직접 연결해서 60 초 안에 실제 NOTAM 219 건을 파싱 에러 0 으로 수신했다

In 60 seconds, we received **219 real NOTAMs from the US FAA production broker** with zero parse errors.

**대학 캡스톤 프로젝트로서는 극히 드문 성과** 입니다. 이유는:

1. Solace JMS 프로토콜 을 써야 함. 일반 REST API 가 아닙니다.
2. TLS 1.2 인증서 검증 — 그냥 접속이 안 됩니다.
3. AIXM 5.1 XML 표준 파서를 직접 구현해야 함.

Why is this hard? **Solace JMS (not REST), TLS 1.2 cert verification, and custom AIXM 5.1 XML parsing**.

슬라이드 아래쪽 빨간 박스에 제가 겪은 고생을 솔직히 적었습니다. **trust store 셋업을 3 번 실패하고 4 번째에 성공**했습니다. 결국 DigiCert Global Root G2 인증서를 수동으로 c_rehash 형식으로 import 해서 해결했습니다.

I failed the trust store setup **three times** and succeeded on the fourth attempt. Eventually manually imported DigiCert Global Root G2 in c_rehash format.

**여러분도 학부생으로서 이런 인프라 수준 integration 에 도전할 수 있다** 는 걸 보여주고 싶어서 자세히 설명드렸습니다.

I share these failures to show that **undergraduate students CAN tackle production-level integrations** — you just need to not give up.

---

## 슬라이드 9 · Kaggle flights.csv EDA (70 초)

네 번째 소스인 Kaggle 데이터는 실시간이 아닌 배치 데이터입니다. **5.7 M 행 × 31 컬럼, 580 MB.** US DOT 의 2015 년 공식 통계.

The fourth source is a batch dataset — **5.7 million rows × 31 columns**, US DOT official 2015 statistics.

슬라이드 오른쪽 위의 핵심 지표를 보시면:
- 지연된 편: **38.8 %** (flights with any delay)
- 취소: 3.4 %
- 평균 도착 지연: 6.2 분
- 최대 지연: **1,971 분** — 약 32 시간 지연된 편이 있습니다 (!)

The worst single delay was **1,971 minutes — over 32 hours!**

슬라이드 아래의 막대 그래프가 이번 발표에서 중요한 발견입니다. **지연의 39.6% 가 '전편 지연 (cascade/reactionary)'** 에서 옵니다.

The bottom bar chart shows the key insight: **39.6% of delays are 'reactionary' — caused by the aircraft's previous leg being late**.

이게 슬라이드 16 에서 제가 설명드릴 **Rotation features** 의 도메인 근거입니다. 이 숫자를 기억해 주세요.

This is the domain justification for the **Rotation features** I'll explain at slide 16. Remember this 40% figure.

---

## 슬라이드 10 · 데이터 포맷의 진화 / Format Evolution (60 초)

같은 항공기 위치 한 건을 세 가지 포맷으로 저장할 수 있습니다.

The same aircraft position can be stored in three different formats.

| 포맷 | 크기 | 장점 | 단점 |
|---|---|---|---|
| JSON | 100 B | 사람 읽기 쉬움 | 스키마 없음, 크기 큼 |
| CSV | 60 B | 가장 가벼움 | 중첩 불가, 타입 없음 |
| **Avro ★** | 35 B | **스키마 강제 + 이진 압축** | 사람 직접 읽기 어려움 |

**초당 수천 건** 이 흐르는 Kafka 에서는 35 바이트 vs 100 바이트가 하루 누적 **수십 GB** 차이를 만듭니다.

At thousands of events per second, 35 B vs 100 B accumulates to **tens of GB/day**.

하지만 크기보다 더 중요한 건 **스키마 강제 (schema enforcement)** 입니다. 다음 슬라이드에서 설명드립니다.

But more important than size is **schema enforcement**, which I'll explain next.

---

## 슬라이드 11 · 왜 Schema Registry? / Why Schema Registry? (75 초)

실제로 있었던 시나리오를 상상해 봅시다.

Imagine this real-world scenario.

**BEFORE** (스키마 없음 · no schema): 개발자 A 가 producer 에 새 필드 `speed_kt` 를 추가합니다. 하지만 기존 consumer 는 옛 필드명 `velocity_ms` 를 기대하고 있죠. 배포하자마자 → **💥 서비스 다운**, consumer 가 `KeyError` 를 던집니다.

Dev A adds `speed_kt` to producer. Consumer still expects `velocity_ms`. Deploy → **crash**, KeyError.

디버깅 질문: **누가 언제 무엇을 바꿨나?** 아무도 모릅니다.

Debugging question: **who changed what when?** Nobody knows.

**AFTER** (Schema Registry + BACKWARD 호환): 개발자 A 가 호환 안 되는 변경을 시도하면 Schema Registry 가 **배포 전에 거부**합니다.

> `409 Conflict: BACKWARD incompatible`

**배포 전에 막힘.** 호환되는 변경 — 예를 들어 default 값이 있는 새 필드 추가 — 는 통과됩니다. 기존 consumer 는 default 값으로 안전하게 동작합니다.

**Blocked before deployment.** Compatible changes (new field with default) pass; old consumers safely use the default.

**BACKWARD 호환** 이라는 개념이 핵심입니다. 이건 "새 consumer 가 옛 데이터도 읽을 수 있어야 한다" 는 뜻이에요. 덕분에 장애 시 **이전 버전으로 롤백이 안전** 합니다.

**BACKWARD** means "new consumers must read old data." This makes **rollback safe during incidents**.

---

## 슬라이드 12 · 전처리 6 단계 파이프라인 / 6-Step Pipeline (45 초)

이제 본격적으로 데이터 가공 단계로 넘어갑니다.

Now we move into data preprocessing.

모든 ML 프로젝트는 결국 **이 6 단계** 를 거칩니다.

Every ML project ultimately goes through **these 6 steps**:

1. **Clean** — 결측·이상·중복 제거
2. **Missing** — NaN 처리 (3 가지 전략)
3. **Feature Eng.** — 시간·거리 분해
4. **Rotation Feats ★** — 도메인 지식 주입 (+335% R²)
5. **Split** — TimeSeriesSplit 시간순
6. **Iceberg** — Bronze/Silver/Gold 저장

슬라이드 하단의 INPUT / OUTPUT 박스를 보세요. **왼쪽은 5.7 M 행 × 사용 불가능한 raw**, 오른쪽은 **400k / 50k / 50k 의 model-ready 학습 세트**. 이 변환이 여기 6 단계에서 일어납니다.

Left box: 5.7M rows of unusable raw. Right box: **400k / 50k / 50k model-ready training set**. Steps 1-6 make this transformation.

---

## 슬라이드 13 · Step 1 · Raw → Clean (60 초)

진짜 원본 데이터가 얼마나 지저분한지 보여드리겠습니다.

Let me show you how dirty real raw data is.

슬라이드 상단의 테이블을 보시면, 분홍색으로 칠해진 행들이 문제가 있는 행입니다.

Pink rows = problematic rows.

- 1-2 행: 완전히 똑같은 레코드가 두 번 있음 — **중복 (duplicate)**
- 3 행: AIRLINE 필드가 빈 칸, DEP_DELAY 가 null — **결측 (missing)**
- 4 행: DEP_DELAY 가 `-9999` — 이건 지연이 아니라 **센서 오류 마커 (sentinel value)** 입니다
- 5 행: DISTANCE 가 `-1` — 거리가 음수? **범위 오류 (invalid range)**

하단의 4 개 박스가 각각의 해결법입니다.

Four solutions at the bottom:

1. **중복 제거 (drop_duplicates)**
2. **결측값 처리** — 다음 슬라이드에서 3 가지 전략
3. **Sentinel 교체** — `-9999` → `NaN` 으로 변환
4. **범위 검증** — `distance > 0` 필터

**이걸 안 하고 바로 모델에 넣으면 GIGO** — Garbage In, Garbage Out.

Skip these and you get **GIGO — Garbage In, Garbage Out**.

---

## 슬라이드 14 · Step 2 · 결측값 (Missing Value) 3 전략 / Three Strategies (60 초)

결측값 처리는 세 가지 전략이 있습니다.

There are three strategies for missing values.

**① Drop** — 그냥 버립니다 (`df.dropna()`). 가장 간단하지만 데이터가 많이 사라집니다.

**② Impute** — 평균이나 중간값으로 채웁니다 (`SimpleImputer(mean)`). 데이터는 유지되지만 분산이 왜곡됩니다.

**③ XGBoost Native ★** — 이게 재밌는 부분입니다. **XGBoost 는 결측값을 '분할 방향' 으로 직접 다룹니다**. 즉 트리의 각 노드에서 "NaN 인 경우 왼쪽 vs 오른쪽 중 어디로 보내야 손실이 최소화되는가" 를 학습합니다.

**XGBoost handles NaN natively** — at each tree node, it learns the optimal direction for missing values (left vs right child).

그래서 XGBoost 가 인기 많은 이유가 여기 있습니다. **다른 모델 (로지스틱 회귀, kNN 등) 은 NaN 이 있으면 아예 학습이 안 됩니다.**

This is a key reason XGBoost is so popular. **Other models like logistic regression or kNN can't even train with NaN present.**

저희는 실제로 **① Impute 와 ③ Native 를 동시에** 씁니다 — sklearn Pipeline 에 SimpleImputer 를 넣고 최종 estimator 는 XGBoost. 이중 안전망.

We use **① + ③ together** — SimpleImputer in the sklearn Pipeline, XGBoost as the final estimator. Double safety net.

---

## 슬라이드 15 · Step 3 · Feature Engineering 기초 / Basics (60 초)

모델은 **문자열을 읽지 못합니다**. 오직 숫자만 이해합니다.

Models **can't read strings**. Only numbers.

슬라이드 왼쪽 빨간 박스: `"2026-04-19 14:30:00"` 이런 datetime 문자열을 그대로 넣으면 모델이 아무 정보도 못 받습니다.

오른쪽 초록 박스: **같은 정보를 6 개 숫자 feature 로 분해**합니다.

- hour = 14
- minute = 30
- dayofweek = 6 (토요일)
- month = 4
- dayofyear = 109
- is_weekend = 1

**왜 이렇게 분해하나?** 하단 남색 박스의 3 가지 이유:

1. **주중 ≠ 주말** — 평일 18 시 혼잡도는 토요일 18 시 혼잡도와 완전히 다릅니다.
2. **월별 패턴** — 여름 7·8 월은 휴가철이라 지연이 많고, 봄 4·5 월은 조용합니다.
3. **시간대 패턴** — 오전 6 시 출발은 거의 정시, 저녁 18 시는 지연이 누적됩니다.

The model needs to **see these patterns independently**. A single datetime string hides them all.

---

## 슬라이드 16 · Step 4 · Rotation Features — 실제 사례 ★ (90 초)

**이 발표에서 가장 중요한 슬라이드입니다.** 잘 들어주세요.

This is **the most important slide in this talk**. Please listen carefully.

왼쪽 남색 박스의 큰 숫자를 보세요.

> **Test R² : 0.10 → 0.43** · +335%

같은 XGBoost 모델인데, **피처 5 개만 추가했을 뿐입니다**. 모델을 키운 것도 아니고 데이터를 더 수집한 것도 아닙니다.

Same XGBoost model. **Just 5 new features added.** No bigger model, no more data.

**어떻게 이게 가능했나?** 오른쪽 박스의 핵심 아이디어:

> "**같은 비행기가 하루에 3-5 번 뜬다.**"
> "Same aircraft flies 3-5 legs per day."

슬라이드 중앙의 비행기 아이콘 HL8281 하루를 보세요.

- 06:00 ICN → CJU, 지연 +2 분 (정상)
- 09:00 CJU → ICN, 지연 +5 분 (조금 누적)
- 12:00 ICN → CJU, 지연 +12 분 (더 누적)
- 15:00 CJU → ICN, 지연 +24 분 (계속 누적)
- 18:00 ICN → CJU, 지연 +45 분 (최악)

**지연은 눈덩이처럼 굴러갑니다 (snowball).** EUROCONTROL 연구에 따르면 전체 지연의 **45% 는 이렇게 누적된 것** 입니다 (reactionary delay).

According to EUROCONTROL research, **45% of all delays are reactionary** — caused by cascading from earlier legs.

기존 모델은 항공편 한 개만 독립적으로 봤습니다. 저희가 추가한 5 개 피처는:

- `rotation_depth` — 당일 몇 번째 leg 인가 (0 = 첫 leg)
- `prev_leg_arr_delay_min` — 직전 leg 가 얼마나 지연됐나
- `scheduled_turnaround_min` — 예정 지상 체류 시간
- `actual_turnaround_min` — 실제 지상 체류 시간
- `is_first_leg_of_day` — 첫 leg 면 1

이 5 개로 R² 가 3.35 배가 됐습니다.

**교훈: 모델을 키우는 것보다 도메인 지식을 feature 로 만드는 것이 훨씬 효과적입니다.**

**Lesson: Domain knowledge as features beats bigger models.**

---

## 슬라이드 17 · Step 5 · Train/Test Split — 흔한 실수 (90 초)

두 번째로 중요한 교훈입니다. **초심자가 가장 많이 하는 치명적 실수.**

The second most important lesson — **the most common critical mistake by beginners**.

왼쪽 빨간 박스: `train_test_split(shuffle=True)` — sklearn 의 기본값입니다. 시간 축을 무시하고 무작위로 섞어서 나눕니다.

`train_test_split(shuffle=True)` is sklearn's default — ignores time, shuffles randomly.

시각화를 보면 **TR · TE · TR · TR · TE · TR · TE · TR · TR · TE** — 시간축을 따라 train 과 test 가 섞여 있습니다.

**💥 미래가 과거 훈련에 섞여 들어갑니다 (future leaks into past training).**

예를 들어 4 월 19 일 데이터로 4 월 15 일 데이터를 예측하는 상황이 생깁니다. 말도 안 되죠. 평가 결과는 비정상적으로 좋게 보입니다 — CV 표준편차 ±0.30. **낙관적 편향 (optimistic bias)** 입니다.

**A model 'predicting' April 15 using April 19 data — nonsense.** Evaluation looks artificially great (CV std ±0.30) — **optimistic bias**.

오른쪽 초록 박스: `TimeSeriesSplit(n_splits=5)` — walk-forward 방식.

**TR TR TR TR TR TR TR · TE TE TE** — 왼쪽 7 칸으로 학습, 오른쪽 3 칸으로 평가. 학습은 항상 과거만, 평가는 항상 미래만.

**Train on past, evaluate on future.**

결과는 CV 표준편차 ±6.14 — 20 배 늘어났습니다. **겉보기엔 나빠 보이지만 이게 정직한 수치** 입니다. 시간대별 성능 변동성이 드러난 것.

CV std jumped 20×, but this is the **honest number** — temporal variance now visible.

저희는 이걸 **ADR-004 에 원칙으로 명시** 하고 전체 파이프라인을 수정했습니다. 여러분 코드에서 `shuffle=True` 가 시계열 데이터에 쓰이고 있다면 **지금 당장 고치세요**.

We codified this in **ADR-004** and fixed the whole pipeline. **If your code uses `shuffle=True` on time-series data, fix it now.**

---

## 슬라이드 18 · Step 6 · Iceberg Medallion (60 초)

마지막 전처리 단계는 저장입니다. 그냥 CSV 에 저장하면 되지 않나? 아닙니다.

The final preprocessing step is storage. Just save CSV? No.

**Apache Iceberg 의 Medallion 아키텍처** — Bronze, Silver, Gold 3 계층으로 분리합니다.

**Bronze** 🥉 — 원본 그대로 저장합니다. JSON, XML 그대로. 나중에 "어라, 이 데이터 다시 처리해야 하네" 할 때 여기로 돌아옵니다.
*Raw as-ingested. Go back here for reprocessing.*

**Silver** 🥈 — 정제 + 조인. 기상 데이터 + 위치 데이터를 합쳐서 flight_features 만듭니다.
*Cleaned + joined. Multiple sources merged.*

**Gold** 🥇 — 모델이 직접 소비하는 테이블. inference_log, anomaly_decisions 같은 감사용 테이블.
*Model-ready + audit trail.*

**왜 3 계층인가?** 하단 남색 박스에 3 가지 이유:

1. **ACID 트랜잭션** — 쓰기 실패해도 일관성 유지
2. **스키마 진화** — 필드 추가/변경 가능
3. **Time travel** — "3 일 전 이 테이블은 어떤 상태였지?" 쿼리 가능 → 사고 조사에 필수

**For incident forensics**, being able to ask "what was this table on April 15?" is essential.

---

## 슬라이드 19 · 이 데이터로 만들 수 있는 것들 / What Can You Build? (60 초)

이제 재밌는 부분입니다. **같은 데이터 셋으로 만들 수 있는 프로젝트가 8 가지 이상 있습니다.**

Now the fun part. **You can build at least 8 different projects with the same dataset.**

- ⏱ 지연 예측 (Delay prediction) — **우리 프로젝트**
- 💰 항공권 가격 예측 (Ticket price forecast)
- 🏢 공항 혼잡도 예측 (Airport congestion)
- ⛽ 연료 소비 최적화 (Fuel efficiency)
- 🗺 운항 경로 최적화 (Route optimization)
- 🌪 기상 영향 분석 (Weather impact)
- ⚠ 이상 탐지 (Anomaly detection) — **우리 프로젝트**
- 👥 승객 수요 예측 (Demand forecasting)

**같은 데이터, 다른 질문, 다른 프로젝트.** 여러분이 선택한 질문이 프로젝트의 정체성을 만듭니다.

**Same data, different questions, different projects.** The question you choose defines your project's identity.

저희는 8 개 중 2 개 — 지연 예측과 이상 탐지 — 를 선택했습니다. **왜?** 둘 다 관제사의 실제 의사결정에 직접 기여하기 때문입니다.

Why these two? Because they **directly impact the ATC's real-time decisions**.

---

## 슬라이드 20 · 우리가 만든 것 / What WE Built (60 초)

우리가 만든 3 가지 기능을 한 슬라이드에 모았습니다.

Three features we built, all on one slide.

**① 지연 예측 + 신뢰구간** — XGBoost Test R² 0.43, Conformal 90% 커버리지. 관제사가 "90% 확률로 6~41 분 지연" 이라는 정량 정보를 받습니다.
*Conformal interval gives quantified uncertainty, not just a point estimate.*

**② 이상 탐지 (7 단계별)** — Isolation Forest 7 개. 단일 모델 대비 alert fatigue −67%. 슬라이드 25 에서 자세히.
*7 phase-specific IF models, 67% fewer false positives.*

**③ AI 관제 어시스턴트** — Qwen2.5-7B + QLoRA + DPO 로 제가 직접 파인튜닝한 한국어 LLM. RAG 로 161 chunks 규정집 참조. 5 초 이내 출처 포함 답변.
*Custom fine-tuned Korean LLM + RAG, 5-second response with citations.*

**세 기능이 독립적으로 보이지만 같은 데이터 파이프라인에서 흘러나옵니다.** 지연 예측은 silver_flight_features, 이상 탐지는 aircraft_phase, RAG 는 ChromaDB — 모두 같은 Iceberg 위에.

**Three features, one pipeline.**

---

## 슬라이드 21 · 모델 1 · 왜 XGBoost? / Why XGBoost? (60 초)

지연 예측 모델로 XGBoost 를 선택한 이유 4 가지.

Four reasons we chose XGBoost for delay prediction.

**① 정확도 (Accuracy)** — tabular 데이터에서 딥러닝과 **동등하거나 더 낫습니다**. 피처 20-30 개 이하 tabular 데이터는 XGBoost 의 홈그라운드.

**② 속도 (Speed)** — 5.7 M 행을 **CPU 만으로 4 분** 에 학습. GPU 필요 없습니다.

**③ 해석성 (Explainability)** — SHAP TreeExplainer 로 "왜 이 항공편이 15 분 지연된다고 예측했는가" 를 각 feature 기여도로 시각화할 수 있습니다. **관제사에게 근거를 제시** 할 수 있다는 뜻.

**④ Robustness** — 결측값 자동 처리, 이상치에 강하고, normalization 필요 없습니다.

실무에서 가장 중요한 건 **3 번 해석성** 입니다. 관제사는 "왜?" 를 물을 때 납득할 만한 답을 원합니다. 딥러닝의 블랙박스로는 그걸 못 합니다.

**In practice, explainability (reason 3) is most important.** ATC wants to know 'why' — deep learning black box fails here.

---

## 슬라이드 22 · XGBoost 작동 원리 / How Gradient Boosting Works (75 초)

XGBoost 가 어떻게 작동하는지 한 줄로 설명드리면:

The one-sentence explanation:

> "여러 개의 약한 모델을 순차적으로 만들되, **이전 모델의 오차에만 집중** 해 학습"
> "Build many weak models sequentially, each focusing on the previous model's errors."

시각화를 보시면:

- **Tree 1** — 첫 예측, 오차 ±15 분. 아직 엉성합니다.
- **Tree 2** — Tree 1 의 잔차 (residual) 에 집중해 학습. 오차 ±8 분.
- **Tree 3** — 남은 오차에 또 집중. 오차 ±3 분.
- ... n = 200 까지 반복. 최종 오차 ±0.5 분.

**최종 예측 = Tree₁ + Tree₂ + Tree₃ + ... + Tree₂₀₀**

비유하자면, **시험 공부할 때 '틀린 문제만 다시 보는 것'** 과 같습니다. 첫 번째 공부에서 70% 맞춤 → 틀린 30% 만 다시 집중 → 그 중 또 틀린 것만 집중 → 반복. 이런 식으로 정답률을 점진적으로 올립니다.

**Analogy**: studying by reviewing only wrong answers. Get 70% → focus on the wrong 30% → focus on what's still wrong → keep improving.

**이게 "gradient" boosting 의 의미** — 매 단계 gradient (손실 함수의 기울기) 를 타고 최적으로 수정해 나간다는 뜻.

---

## 슬라이드 23 · XGBoost 실제 결과 / Actual Results (60 초)

실제 우리 프로젝트의 결과입니다. Sprint 별 Test R² 추이.

Actual results in our project, by sprint.

- **기본 XGBoost (baseline)**: R² 0.10
- **+ TimeSeriesSplit (P0)**: R² 0.10 — **수치는 그대로지만 정직해짐**
- **+ Rotation features ★ (P1)**: R² **0.43** — 여기서 3.35 배 점프
- **+ Conformal interval (P1+)**: R² 0.43 유지 + 구간 추가

**주목할 점: P0 에서 TimeSeriesSplit 으로 바꿨을 때 수치가 안 올라갔습니다.** 왜냐하면 TimeSeriesSplit 은 '더 좋은 모델' 을 만들어주는 게 아니라 '**더 정직한 평가**' 를 해줄 뿐이기 때문입니다.

Notice: **P0 didn't improve the number.** Because TimeSeriesSplit doesn't make a better model — it gives a **more honest evaluation**.

**진짜 향상은 P1 Rotation features** 가 만들었습니다. 다시 강조: 모델을 키우는 것보다 도메인 지식을 feature 로 만드는 것이 효과적입니다.

**Real improvement came from P1.** Again: domain knowledge > bigger model.

슬라이드 아래의 최종 지표:
- Test RMSE 22.61 분
- Test R² 0.43
- Conformal coverage 정확히 90.00%
- 응답 시간 p95 42 ms

---

## 슬라이드 24 · 모델 2 · 왜 Isolation Forest? / Why IF? (75 초)

두 번째 모델은 이상 탐지 (anomaly detection) 용 Isolation Forest 입니다.

Second model: Isolation Forest for anomaly detection.

**핵심 아이디어:**
> "이상치는 소수이고 정상과 거리가 멀어서 **무작위 분할로 빨리 고립** 된다."
> "Anomalies are few and far — they get isolated quickly under random partitioning."

시각화 왼쪽 초록 박스: 정상점은 트리에서 **깊게 내려가야** 고립됩니다. path length 8+ splits.

*Normal point: deep tree, 8+ splits to isolate.*

오른쪽 빨간 박스: 이상점은 **몇 번의 분할로 바로 고립** 됩니다. path length 2-3 splits.

*Anomaly: shallow tree, 2-3 splits.*

**path length 자체가 anomaly score 입니다.** 짧으면 이상, 길면 정상. 매우 직관적.

**Path length IS the anomaly score.** Short = anomalous, long = normal. Beautifully intuitive.

**왜 다른 모델이 아닌가?** 하단 박스의 3 가지 이유:

1. **라벨 없음 (no labels)** — 항공 사고는 희귀해서 지도학습 불가능
2. **O(n log n) 속도** — Autoencoder 나 One-class SVM 보다 훨씬 빠름
3. **직관적** — path length 로 해석 가능

**Autoencoder 를 쓰면 GPU 필요 + 학습 불안정 + 블랙박스.** IF 는 이 셋 다 해결합니다.

**Autoencoder: GPU + unstable training + black box.** IF solves all three.

---

## 슬라이드 25 · Per-phase IF × 7 (75 초)

IF 를 7 개 만든 이유를 설명드리겠습니다.

Why 7 models instead of 1?

상단 빨간 박스의 문제:

> CRUISE 중 30,000 ft 는 정상인데, LANDING 중 30,000 ft 는 완전 비정상.

**30,000 ft during CRUISE = normal, but 30,000 ft during LANDING = abnormal.**

단일 모델은 둘을 구분 못합니다. 결과: TAXI 중 급가속을 CRUISE 임계값 위반으로 오인 → false positive 폭주 → **alert fatigue**.

Single model confuses them. Result: **alert fatigue**.

해결: **7 개의 비행 단계마다 별도 IF + contamination 별도 튜닝**.

- TAXI contamination = 0.02 (조용한 구간, 이상 거의 없음)
- TAKEOFF 0.03, CLIMB 0.04, CRUISE 0.05, DESCENT 0.04
- **APPROACH 0.06, LANDING 0.06** — 사고가 가장 빈발하는 구간이라 민감하게

각 phase 별로 contamination 을 **3 배 차이** 로 튜닝했습니다. TAXI 2% 부터 APPROACH/LANDING 6% 까지.

Each phase tuned with **3× range of contamination** — from 2% (TAXI) to 6% (APPROACH/LANDING).

**결과 (하단 남색 박스): False Positive −67%.** Alert fatigue 가 대폭 완화됐습니다. v2.1.10 (ADR-006) 에서 서빙에도 실제 wire-up 완료.

---

## 슬라이드 26 · Conformal Prediction (75 초)

마지막 핵심 기법. 점 예측 (point) 대 구간 예측 (interval).

Last technique. Point vs interval prediction.

왼쪽 빨간 박스 — BEFORE:
> "15 분 지연"

이 한 숫자는 얼마나 믿어야 할까요? **실제로 5 분일 수도 40 분일 수도 있습니다.**

*How much should you trust this? Actually could be 5 or 40 minutes.*

관제사가 이 숫자만 보고 어떻게 승객 안내를 하나요? 근거 없는 "high/medium/low confidence" 분류로는 부족합니다.

오른쪽 초록 박스 — AFTER (Conformal):
> "**90% 확률로 6 ~ 41 분 지연**"

이건 **수학적으로 보장** 된 구간입니다. 분포 가정 없이 (distribution-free).

*Mathematically guaranteed coverage, distribution-free.*

MAPIE 라이브러리로 구현. **실측 coverage 가 정확히 90.00%** 나온 것이 증거입니다.

이제 관제사는:

> "최악의 경우 41 분까지 지연 가능 → 승객 안내 준비"

이렇게 **정량적 의사결정** 을 할 수 있습니다.

**ATC can now make quantified decisions: 'worst case 41 min → prepare passenger announcement'.**

---

## 슬라이드 27 · 데이터 → 의사결정 End-to-End (60 초)

모든 걸 연결해 보겠습니다. 비행기가 공중에 떠 있을 때부터 관제사 화면에 알림이 뜰 때까지 **7 단계** 가 5 초 이내에 흐릅니다.

Let me connect everything. From airborne aircraft to alert on ATC screen — 7 stages, all within 5 seconds.

1. **ADS-B 수신** — 비행기가 위치 방송 → 지상 수신기 → OpenSky
2. **Kafka 도착** — flight-position 토픽에 Avro 메시지
3. **Iceberg Silver** — flight_features 테이블에 조인
4. **XGBoost 예측** — delay = 20 min, 42 ms
5. **Conformal 구간** — [12, 40] min, 90% 확률
6. **RAG + LLM 조언** — "FAA AIM 7-1 에 따라 승객 안내 준비"
7. **관제사 대시보드** — <5 s 전체 end-to-end

**이 전체가 5 초 이내에 끝납니다.** 각 단계의 지연: Kafka 100 ms, Iceberg 500 ms, XGBoost 42 ms, Conformal 100 ms, LLM 2-3 s, 나머지 network.

**End-to-end under 5 seconds.** LLM is the slow part (2-3 s); everything else is sub-second.

---

## 슬라이드 28 · 학생을 위한 핵심 교훈 / Key Takeaways (90 초)

이 발표에서 여러분이 가져갈 5 가지 교훈입니다.

Five takeaways to remember.

**① 데이터는 raw 부터 완벽하지 않다.**
*Raw data is never clean.* — cleaning 단계를 절대 건너뛰지 마라.

**② Feature engineering > 모델 크기.**
*Features beat model size.* — 실제 증거: P1 에서 5 features 추가로 R² +335%.

**③ 시계열은 절대 shuffle 하지 마라.**
*Never shuffle time-series.* — temporal leakage 는 가장 흔한 치명적 실수.

**④ 모델 선택은 정확도만이 아니다.**
*Accuracy is not the only metric.* — 해석성 · 운영성 · 유지비 모두 고려.

**⑤ 도메인 지식이 곧 경쟁력.**
*Domain knowledge = competitive edge.* — EUROCONTROL 의 '지연 45% 는 reactionary' 라는 연구 한 줄이 Rotation features 설계의 씨앗이 됐습니다.

**Especially 2 and 3 are where beginners most often fail.** 우리 프로젝트의 P0/P1 sprint 가 그 증거입니다.

**2 and 3 are the most commonly failed by beginners.** Our P0/P1 sprints are the proof.

---

## 슬라이드 29 · Q&A / 질의응답 (질문 시간만큼)

질문을 받겠습니다. 예상 질문 5 개를 미리 준비해 왔습니다.

I'll take questions. I prepared 5 likely ones.

**Q1: 왜 Iceberg 가 그냥 parquet 보다 낫나요?**
*A: Plain parquet 은 파일일 뿐. Iceberg 는 catalog + ACID 트랜잭션 + 스키마 진화 + time-travel. "3 일 전 상태" 쿼리 같은 게 parquet 으론 불가능.*

**Q2: Conformal 말고 Bayesian CI 는 안 되나요?**
*A: Bayesian 은 prior 가정 필요. Conformal 은 분포 가정 없음 (distribution-free). 데이터가 Bayesian 가정을 어기면 구간이 깨지지만 Conformal 은 안 깨집니다.*

**Q3: Per-phase 7 개 대신 phase 를 feature 로 넣으면?**
*A: 단일 모델은 contamination 을 모든 phase 에 동일하게 써야 합니다. phase 별 3 배 차이 (TAXI 2% ↔ LANDING 6%) 를 반영 못 합니다.*

**Q4: 5.7 M 행 전부 말고 샘플만 써도 되나요?**
*A: 10% sampling 했습니다. 다만 chronological 하게 뽑아서 시간 편향은 없습니다. 500k 행이면 충분한 통계.*

**Q5: RAG 161 chunks 로 충분한가요?**
*A: RAGAs 평가에서 faithfulness 0.91, context_precision 0.85 로 검증됐습니다. 국내선 관제 용도로는 충분. 국제선으로 확장 시 추가 필요.*

---

## 슬라이드 30 · 감사합니다 / Thank You (30 초)

감사합니다. Thank you.

오늘 발표의 **핵심 세 가지** 를 다시 짧게:

1. **데이터는 전처리가 핵심** — 6 단계 파이프라인
2. **Feature engineering 이 모델보다 강력** — +335% 사례
3. **시계열은 절대 shuffle 금지** — ADR-004 원칙

**The three core lessons**: preprocessing pipeline · features > model · never shuffle time-series.

자원은 슬라이드에 있습니다:
- GitHub: `github.com/biz-doublej/SkyOps-Intelligence`
- 데이터 문서: `docs/data_collection.md`
- Reproduction guide: 564 lines
- ADR 7 개: `docs/adr/`
- 연락: doublej.biz01@gmail.com

**질문이 더 있으시면 발표 후에도 편하게 말씀해 주세요.**

**If you have more questions, feel free to ask after the talk.**

감사합니다. Thank you.

---

## 📎 발표자용 체크리스트 / Presenter's Checklist

- [ ] 슬라이드 8 (SWIM) — "대학 프로젝트로 드문 성과" 강조 · stress uniqueness
- [ ] 슬라이드 16 (Rotation +335%) — **천천히**, 숫자 각인
- [ ] 슬라이드 17 (shuffle) — **지금 당장 고치라** 는 톤으로
- [ ] 슬라이드 22 (XGBoost) — "틀린 문제만 다시 보는 것" 비유 사용
- [ ] 슬라이드 28 (Takeaways) — 5 개 각각 손가락 펴면서 카운트
- [ ] Q&A — 답변 짧게, 구체 숫자 + ADR 번호로 뒷받침

## 📎 한-영 핵심 용어 노트 / Korean-English Term Cheat Sheet

| 한국어 | English | 슬라이드 |
|---|---|---|
| 측정값 | quantified observation | 3 |
| 시계열 | time-series | 4, 17 |
| 스키마 강제 | schema enforcement | 10, 11 |
| BACKWARD 호환 | BACKWARD compatibility | 11 |
| 결측값 | missing value | 14 |
| Sentinel 값 | sentinel value | 13 |
| Feature Engineering | feature engineering | 15, 16 |
| Rotation 피처 | rotation features | 16 |
| Reactionary 지연 | reactionary delay | 16 |
| Temporal leakage | temporal leakage | 17 |
| Walk-forward | walk-forward validation | 17 |
| Medallion 아키텍처 | medallion architecture | 18 |
| Time-travel | time-travel | 18 |
| Gradient Boosting | gradient boosting | 22 |
| 잔차 | residual | 22 |
| Path length | path length | 24 |
| 비지도 학습 | unsupervised learning | 24 |
| Contamination | contamination | 25 |
| Alert fatigue | alert fatigue | 25 |
| 점 예측 / 구간 예측 | point prediction / interval prediction | 26 |
| 신뢰구간 | confidence interval | 26 |
| 분포 가정 없음 | distribution-free | 26 |
| 커버리지 | coverage | 26 |
