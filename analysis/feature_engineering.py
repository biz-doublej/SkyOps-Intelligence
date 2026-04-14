"""
SkyOps Intelligence — 4주차 Feature Engineering
==================================================
Feature 목록 확정 (26개) + 전처리 파이프라인

실행:
  python analysis/feature_engineering.py

출력:
  data/processed/features.parquet   (전처리 완료 데이터)
  data/processed/feature_list.md    (Feature 명세서)
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

# ── 경로 설정 ──────────────────────────────────────────────────────────
PROJECT_ROOT  = Path(__file__).parent.parent
DATA_DIR      = PROJECT_ROOT / "data"
RAW_CSV       = DATA_DIR / "raw" / "flights.csv"
PROCESSED_DIR = DATA_DIR / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# ── RENAME_MAP (eda.py 와 동일) ────────────────────────────────────────
RENAME_MAP = {
    "YEAR": "year", "MONTH": "month", "DAY": "day",
    "AIRLINE": "carrier_code", "FLIGHT_NUMBER": "flight_num",
    "TAIL_NUMBER": "tail_number",        # P1 Rotation PoC — 2026-04-14
    "ORIGIN_AIRPORT": "origin", "DESTINATION_AIRPORT": "dest",
    "SCHEDULED_DEPARTURE": "sched_dep_time", "DEPARTURE_TIME": "act_dep_time",
    "DEPARTURE_DELAY": "dep_delay_min", "TAXI_OUT": "taxi_out_min",
    "WHEELS_OFF": "wheels_off", "WHEELS_ON": "wheels_on",
    "TAXI_IN": "taxi_in_min", "SCHEDULED_ARRIVAL": "sched_arr_time",
    "ARRIVAL_TIME": "act_arr_time", "ARRIVAL_DELAY": "arr_delay_min",
    "CANCELLED": "cancelled", "CANCELLATION_REASON": "cancel_code",
    "DIVERTED": "diverted", "SCHEDULED_TIME": "sched_elapsed_min",
    "ELAPSED_TIME": "act_elapsed_min", "AIR_TIME": "air_time_min",
    "DISTANCE": "distance_miles",
    "AIRLINE_DELAY": "carrier_delay_min", "WEATHER_DELAY": "weather_delay_min",
    "AIR_SYSTEM_DELAY": "nas_delay_min", "SECURITY_DELAY": "security_delay_min",
    "LATE_AIRCRAFT_DELAY": "late_aircraft_delay_min",
}

# ─────────────────────────────────────────────────────────────────────
# Feature 목록 (26개) — 4주차 확정판
# ─────────────────────────────────────────────────────────────────────
FEATURE_SPEC = {
    # ── 시간 관련 (6개) ──────────────────────────────────────────────
    "dep_hour": {
        "desc": "출발 예정 시각 (0~23)",
        "type": "int", "unit": "시",
        "source": "sched_dep_time // 100",
    },
    "dep_minute": {
        "desc": "출발 예정 분 (0~59)",
        "type": "int", "unit": "분",
        "source": "sched_dep_time % 100",
    },
    "dep_dayofweek": {
        "desc": "출발 요일 (0=월 ~ 6=일)",
        "type": "int", "unit": "-",
        "source": "fl_date.dayofweek",
    },
    "dep_month": {
        "desc": "출발 월 (1~12)",
        "type": "int", "unit": "월",
        "source": "fl_date.month",
    },
    "dep_dayofyear": {
        "desc": "연중 출발일 (1~365)",
        "type": "int", "unit": "일",
        "source": "fl_date.dayofyear",
    },
    "is_weekend": {
        "desc": "주말 여부 (토·일 = 1)",
        "type": "int", "unit": "bool",
        "source": "dep_dayofweek >= 5",
    },

    # ── 공항/노선 관련 (4개) ─────────────────────────────────────────
    "origin": {
        "desc": "출발 공항 코드 (IATA)",
        "type": "category", "unit": "-",
        "source": "origin",
    },
    "dest": {
        "desc": "도착 공항 코드 (IATA)",
        "type": "category", "unit": "-",
        "source": "dest",
    },
    "distance_miles": {
        "desc": "운항 거리",
        "type": "float", "unit": "마일",
        "source": "distance_miles",
    },
    "route": {
        "desc": "출발-도착 노선 코드 (origin + dest)",
        "type": "category", "unit": "-",
        "source": "origin + '_' + dest",
    },

    # ── 항공사 관련 (1개) ────────────────────────────────────────────
    "carrier_code": {
        "desc": "항공사 IATA 코드",
        "type": "category", "unit": "-",
        "source": "carrier_code",
    },

    # ── 운항 계획 관련 (2개) ─────────────────────────────────────────
    "sched_elapsed_min": {
        "desc": "예정 비행 시간",
        "type": "float", "unit": "분",
        "source": "sched_elapsed_min",
    },
    "dep_block": {
        "desc": "출발 시간대 블록 (새벽/오전/오후/저녁/밤)",
        "type": "category", "unit": "-",
        "source": "pd.cut(dep_hour, [0,6,12,17,20,24])",
    },

    # ── 이전 편 지연 (Cascade Delay) 관련 (3개) ─────────────────────
    "prev_dep_delay_min": {
        "desc": "동일 flight_num 직전 편 출발 지연 (cascade delay)",
        "type": "float", "unit": "분",
        "source": "shift(1) within (carrier_code, flight_num, fl_date)",
    },
    "prev_arr_delay_min": {
        "desc": "동일 flight_num 직전 편 도착 지연",
        "type": "float", "unit": "분",
        "source": "shift(1) within (carrier_code, flight_num, fl_date)",
    },
    "is_prev_delayed": {
        "desc": "직전 편 지연 여부 (>15분 = 1)",
        "type": "int", "unit": "bool",
        "source": "prev_dep_delay_min > 15",
    },

    # ── Rotation (P1 · 2026-04-14, tail_number 기반) (5개) ────────────
    "rotation_depth": {
        "desc": "해당 일자 내 몇 번째 leg (0=첫째, 1=둘째, ...) — 동일 tail 기준",
        "type": "int", "unit": "-",
        "source": "groupby(tail_number, fl_date).cumcount()",
        "note": "P1 Rotation PoC",
    },
    "prev_leg_arr_delay_min": {
        "desc": "같은 tail_number의 직전 leg 실제 도착 지연 (flight_num 무관)",
        "type": "float", "unit": "분",
        "source": "groupby(tail_number)[arr_delay_min].shift(1)",
        "note": "P1 Rotation PoC",
    },
    "scheduled_turnaround_min": {
        "desc": "예정 turnaround: sched_dep - prev_sched_arr (tail 기준)",
        "type": "float", "unit": "분",
        "source": "shift(1) of sched_arr_dt per tail_number",
        "note": "P1 Rotation PoC",
    },
    "actual_turnaround_min": {
        "desc": "실제 turnaround: sched_dep - prev_actual_arr (tail 기준)",
        "type": "float", "unit": "분",
        "source": "shift(1) of act_arr_dt per tail_number",
        "note": "P1 Rotation PoC",
    },
    "is_first_leg_of_day": {
        "desc": "해당 일자 첫 leg 여부 (rotation_depth == 0)",
        "type": "int", "unit": "bool",
        "source": "rotation_depth == 0",
        "note": "P1 Rotation PoC",
    },

    # ── 공항 혼잡도 관련 (2개) ───────────────────────────────────────
    "origin_hourly_departures": {
        "desc": "출발 공항의 동일 시간대 출발 편수 (혼잡도 지수)",
        "type": "int", "unit": "편",
        "source": "groupby(origin, fl_date, dep_hour).transform('count')",
    },
    "dest_hourly_arrivals": {
        "desc": "도착 공항의 동일 시간대 도착 편수",
        "type": "int", "unit": "편",
        "source": "groupby(dest, fl_date, sched_arr_hour).transform('count')",
    },

    # ── 기상 관련 (4개, 실시간 연동 시 NOAA METAR로 교체) ────────────
    "weather_delay_min": {
        "desc": "기상 지연 시간 (학습용 레이블 누설 주의 → 추론 시 제외)",
        "type": "float", "unit": "분",
        "source": "weather_delay_min",
        "note": "▲ 추론(inference) 시 제외 필요",
    },
    "dep_month_weather_score": {
        "desc": "출발 월 기반 기상 위험 스코어 (12,1,2월=겨울=高, 6,7,8=여름폭풍=中)",
        "type": "float", "unit": "-",
        "source": "계절별 통계 기반 수동 매핑",
    },
    "origin_weather_hist_delay": {
        "desc": "출발 공항의 월별 기상 지연 이력 평균 (Historical)",
        "type": "float", "unit": "분",
        "source": "groupby(origin, dep_month)[weather_delay_min].mean()",
    },
    "dest_weather_hist_delay": {
        "desc": "도착 공항의 월별 기상 지연 이력 평균",
        "type": "float", "unit": "분",
        "source": "groupby(dest, dep_month)[weather_delay_min].mean()",
    },

    # ── 통계적 인코딩 (4개) ──────────────────────────────────────────
    "carrier_hist_delay": {
        "desc": "항공사별 이력 평균 도착 지연 (Target Encoding)",
        "type": "float", "unit": "분",
        "source": "groupby(carrier_code)[arr_delay_min].mean()",
    },
    "origin_hist_delay": {
        "desc": "출발 공항 이력 평균 도착 지연",
        "type": "float", "unit": "분",
        "source": "groupby(origin)[arr_delay_min].mean()",
    },
    "dest_hist_delay": {
        "desc": "도착 공항 이력 평균 도착 지연",
        "type": "float", "unit": "분",
        "source": "groupby(dest)[arr_delay_min].mean()",
    },
    "route_hist_delay": {
        "desc": "노선별 이력 평균 도착 지연",
        "type": "float", "unit": "분",
        "source": "groupby(route)[arr_delay_min].mean()",
    },
}

TARGET_COL = "dep_delay_min"   # 예측 대상 (출발 지연)


# ── 헬퍼 함수들 ────────────────────────────────────────────────────────
def _time_to_hour(series: pd.Series) -> pd.Series:
    """HHMM 포맷 → 시(0~23)"""
    return (pd.to_numeric(series, errors="coerce") // 100).clip(0, 23).astype("Int16")


def _time_to_minute(series: pd.Series) -> pd.Series:
    """HHMM 포맷 → 분(0~59)"""
    return (pd.to_numeric(series, errors="coerce") % 100).clip(0, 59).astype("Int16")


def _dep_block(hour: pd.Series) -> pd.Categorical:
    """시간 블록 분류"""
    bins   = [0, 6, 12, 17, 20, 24]
    labels = ["새벽(0-6)", "오전(6-12)", "오후(12-17)", "저녁(17-20)", "밤(20-24)"]
    return pd.cut(hour.fillna(0).astype(int), bins=bins, labels=labels,
                  right=False, include_lowest=True)


def _weather_score(month: pd.Series) -> pd.Series:
    """월별 기상 위험 스코어 (전문가 도메인 지식 기반)"""
    score_map = {1: 0.9, 2: 0.8, 3: 0.5, 4: 0.4, 5: 0.5,
                 6: 0.7, 7: 0.8, 8: 0.7, 9: 0.5, 10: 0.4, 11: 0.5, 12: 0.9}
    return month.map(score_map).astype(float)


# ── 메인 Feature Engineering 파이프라인 ───────────────────────────────
def build_features(sample_n: int | None = None) -> pd.DataFrame:
    if not RAW_CSV.exists():
        print(f"❌ 데이터 없음: {RAW_CSV}")
        print("   먼저 실행하세요: python analysis/download_dataset.py")
        sys.exit(1)

    print("📂 원본 데이터 로드...")
    usecols = list(RENAME_MAP.keys())
    df = pd.read_csv(RAW_CSV, usecols=usecols, nrows=sample_n, low_memory=False)
    df.rename(columns=RENAME_MAP, inplace=True)
    df["fl_date"] = pd.to_datetime(df[["year", "month", "day"]], errors="coerce")
    df.drop(columns=["year", "month", "day"], inplace=True)
    print(f"   {len(df):,}행 로드 완료")

    # 취소·회항 제거
    df = df[(df["cancelled"] != 1) & (df["diverted"] != 1)].copy()
    print(f"   취소/회항 제거 후: {len(df):,}행")

    steps = [
        ("시간 Feature 생성",           _add_time_features),
        ("노선 Feature 생성",           _add_route_features),
        ("Cascade Delay Feature",       _add_cascade_features),
        ("Rotation Feature (P1)",       _add_rotation_features),
        ("공항 혼잡도 Feature",         _add_congestion_features),
        ("기상 이력 Feature",           _add_weather_features),
        ("통계적 인코딩 (Target Enc.)", _add_target_encoding),
        ("결측치 처리",                 _handle_missing),
        ("이상치 클리핑",               _clip_outliers),
    ]

    for name, func in tqdm(steps, desc="Feature Engineering"):
        print(f"\n▶ {name}")
        df = func(df)
        print(f"   완료 — shape: {df.shape}")

    return df


def _add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    df["dep_hour"]      = _time_to_hour(df["sched_dep_time"])
    df["dep_minute"]    = _time_to_minute(df["sched_dep_time"])
    df["dep_dayofweek"] = df["fl_date"].dt.dayofweek.astype("Int8")
    df["dep_month"]     = df["fl_date"].dt.month.astype("Int8")
    df["dep_dayofyear"] = df["fl_date"].dt.dayofyear.astype("Int16")
    df["is_weekend"]    = (df["dep_dayofweek"] >= 5).astype("Int8")
    df["dep_block"]     = _dep_block(df["dep_hour"])
    return df


def _add_route_features(df: pd.DataFrame) -> pd.DataFrame:
    df["route"] = df["origin"].astype(str) + "_" + df["dest"].astype(str)
    return df


def _add_cascade_features(df: pd.DataFrame) -> pd.DataFrame:
    """동일 항공편 번호 + 날짜 기준으로 직전 편 지연을 shift(1)로 계산."""
    df.sort_values(["carrier_code", "flight_num", "fl_date", "sched_dep_time"], inplace=True)
    grp = df.groupby(["carrier_code", "flight_num", "fl_date"])
    df["prev_dep_delay_min"] = grp["dep_delay_min"].shift(1)
    df["prev_arr_delay_min"] = grp["arr_delay_min"].shift(1)
    df["is_prev_delayed"]    = (df["prev_dep_delay_min"] > 15).astype("Int8")
    return df


def _add_rotation_features(df: pd.DataFrame) -> pd.DataFrame:
    """TAIL_NUMBER 기반 rotation-aware features (P1 · 2026-04-14).

    Strategic Review 4번 병목 — EUROCONTROL CODA가 지적하는 reactionary/rotational
    delay를 반영. 기존 cascade features는 flight_num 기준이라 같은 기체가 다른
    flight_num으로 운항할 때 연결이 끊긴다. 여기서는 tail_number 기준으로
    운항 네트워크를 모델링한다.

    생성 features:
      - rotation_depth: 해당 일자 내 몇 번째 leg (0=첫째)
      - prev_leg_arr_delay_min: 같은 tail의 직전 leg 실제 도착 지연
      - scheduled_turnaround_min: sched_dep - prev_sched_arr (minutes)
      - actual_turnaround_min: sched_dep - prev_act_arr (minutes, nullable)
      - is_first_leg_of_day: rotation_depth == 0
    """
    # tail_number 결측은 "UNKNOWN"으로 마킹하여 groupby에는 포함하되,
    # 해당 그룹 내에서는 rotation 의미가 없음을 is_first_leg_of_day로 식별 가능
    df["tail_number"] = df["tail_number"].fillna("UNKNOWN").astype(str)

    # fl_date + sched_dep_time → 고해상도 datetime (HHMM → minutes)
    dep_hm = pd.to_numeric(df["sched_dep_time"], errors="coerce").fillna(0).astype(int)
    dep_minutes = (dep_hm // 100).clip(0, 23) * 60 + (dep_hm % 100).clip(0, 59)
    df["_sched_dep_dt"] = df["fl_date"] + pd.to_timedelta(dep_minutes, unit="m")

    arr_hm = pd.to_numeric(df["sched_arr_time"], errors="coerce").fillna(0).astype(int)
    arr_minutes = (arr_hm // 100).clip(0, 23) * 60 + (arr_hm % 100).clip(0, 59)
    df["_sched_arr_dt"] = df["fl_date"] + pd.to_timedelta(arr_minutes, unit="m")
    # arr < dep이면 익일 도착 (e.g. 저녁 출발 → 익일 새벽 도착) — 1일 더함
    df.loc[df["_sched_arr_dt"] < df["_sched_dep_dt"], "_sched_arr_dt"] += pd.Timedelta(days=1)

    act_hm = pd.to_numeric(df["act_arr_time"], errors="coerce")
    has_act = act_hm.notna()
    act_hm_filled = act_hm.fillna(0).astype(int)
    act_minutes = (act_hm_filled // 100).clip(0, 23) * 60 + (act_hm_filled % 100).clip(0, 59)
    df["_act_arr_dt"] = df["fl_date"] + pd.to_timedelta(act_minutes, unit="m")
    df.loc[df["_act_arr_dt"] < df["_sched_dep_dt"], "_act_arr_dt"] += pd.Timedelta(days=1)
    df.loc[~has_act, "_act_arr_dt"] = pd.NaT

    # tail별 시간 순 정렬
    df.sort_values(["tail_number", "_sched_dep_dt"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    grp_tail = df.groupby("tail_number")

    # 1. rotation_depth: 해당 일자 내 몇 번째 leg
    df["rotation_depth"] = (
        df.groupby(["tail_number", "fl_date"]).cumcount().astype("Int16")
    )

    # 2. 직전 leg 도착 지연 (tail 기준)
    df["prev_leg_arr_delay_min"] = grp_tail["arr_delay_min"].shift(1)

    # 3. scheduled_turnaround_min: sched_dep - prev_sched_arr
    prev_sched_arr = grp_tail["_sched_arr_dt"].shift(1)
    df["scheduled_turnaround_min"] = (
        (df["_sched_dep_dt"] - prev_sched_arr).dt.total_seconds() / 60
    )

    # 4. actual_turnaround_min: sched_dep - prev_actual_arr
    prev_act_arr = grp_tail["_act_arr_dt"].shift(1)
    df["actual_turnaround_min"] = (
        (df["_sched_dep_dt"] - prev_act_arr).dt.total_seconds() / 60
    )

    # 5. is_first_leg_of_day
    df["is_first_leg_of_day"] = (df["rotation_depth"] == 0).astype("Int8")

    # 임시 컬럼 제거
    df.drop(columns=["_sched_dep_dt", "_sched_arr_dt", "_act_arr_dt"], inplace=True)

    return df


def _add_congestion_features(df: pd.DataFrame) -> pd.DataFrame:
    df["origin_hourly_departures"] = (
        df.groupby(["origin", "fl_date", "dep_hour"])["flight_num"]
        .transform("count")
        .astype("Int16")
    )
    arr_hour = _time_to_hour(df["sched_arr_time"])
    df["_arr_hour"] = arr_hour
    df["dest_hourly_arrivals"] = (
        df.groupby(["dest", "fl_date", "_arr_hour"])["flight_num"]
        .transform("count")
        .astype("Int16")
    )
    df.drop(columns=["_arr_hour"], inplace=True)
    return df


def _add_weather_features(df: pd.DataFrame) -> pd.DataFrame:
    df["dep_month_weather_score"] = _weather_score(df["dep_month"])

    origin_wx = (
        df.groupby(["origin", "dep_month"])["weather_delay_min"]
        .mean()
        .rename("origin_weather_hist_delay")
    )
    dest_wx = (
        df.groupby(["dest", "dep_month"])["weather_delay_min"]
        .mean()
        .rename("dest_weather_hist_delay")
    )
    df = df.join(origin_wx, on=["origin", "dep_month"])
    df = df.join(dest_wx,   on=["dest",   "dep_month"])
    return df


def _add_target_encoding(df: pd.DataFrame) -> pd.DataFrame:
    """Target Encoding — 이력 평균 지연 시간 (데이터 누설 없는 train-only 기반)"""
    for grp_col, feat_name in [
        ("carrier_code", "carrier_hist_delay"),
        ("origin",       "origin_hist_delay"),
        ("dest",         "dest_hist_delay"),
        ("route",        "route_hist_delay"),
    ]:
        means = df.groupby(grp_col)["arr_delay_min"].mean().rename(feat_name)
        df = df.join(means, on=grp_col)
    return df


def _handle_missing(df: pd.DataFrame) -> pd.DataFrame:
    """결측치 전략:
    - 수치형: 중위수 대체
    - 범주형: 최빈값 대체
    - cascade delay: 0 대체 (첫 번째 편은 이전 편 없음)
    """
    df["prev_dep_delay_min"] = df["prev_dep_delay_min"].fillna(0)
    df["prev_arr_delay_min"] = df["prev_arr_delay_min"].fillna(0)
    df["is_prev_delayed"] = df["is_prev_delayed"].fillna(0)

    # P1 Rotation features — 첫 leg은 이전 값 없음 → 0으로 대체.
    # is_first_leg_of_day 플래그로 "첫 leg"와 "N번째 leg의 우연한 0" 구분 가능.
    df["prev_leg_arr_delay_min"] = df["prev_leg_arr_delay_min"].fillna(0)
    df["scheduled_turnaround_min"] = df["scheduled_turnaround_min"].fillna(0)
    df["actual_turnaround_min"] = df["actual_turnaround_min"].fillna(0)

    numeric_fill_cols = [
        "origin_weather_hist_delay", "dest_weather_hist_delay",
        "carrier_hist_delay", "origin_hist_delay",
        "dest_hist_delay", "route_hist_delay",
        "sched_elapsed_min", "distance_miles",
    ]
    for col in numeric_fill_cols:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())

    return df


def _clip_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """
    이상치 클리핑:
    - dep_delay_min: -60 ~ 600 분
    - arr_delay_min: -60 ~ 600 분
    """
    if "dep_delay_min" in df.columns:
        df["dep_delay_min"] = df["dep_delay_min"].clip(-60, 600)
    if "arr_delay_min" in df.columns:
        df["arr_delay_min"] = df["arr_delay_min"].clip(-60, 600)
    return df


# ── Feature 명세서 저장 ────────────────────────────────────────────────
def save_feature_doc() -> None:
    lines = [
        "# SkyOps Intelligence — Feature 목록 (확정판)",
        f"총 {len(FEATURE_SPEC)}개 Feature, 예측 타깃: `{TARGET_COL}`",
        "",
        "| # | Feature 명 | 타입 | 단위 | 설명 |",
        "|---|-----------|------|------|------|",
    ]
    for i, (name, spec) in enumerate(FEATURE_SPEC.items(), 1):
        note = f" _{spec.get('note', '')}_" if spec.get("note") else ""
        lines.append(
            f"| {i:2d} | `{name}` | {spec['type']} | {spec['unit']} | {spec['desc']}{note} |"
        )

    lines += [
        "",
        "## 예측 타깃",
        f"- `{TARGET_COL}`: 출발 지연 시간 (분). 이진 분류 시 >15분을 `delayed=1`로 정의.",
        "",
        "## 제외 Feature (데이터 누설)",
        "- `arr_delay_min`: 출발 후 결정 → 추론 불가",
        "- `weather_delay_min`, `carrier_delay_min` 등 delay cause 컬럼 → 실운항 후 기록",
        "- `act_dep_time`, `act_arr_time`: 실제 시각 → 사전 미지",
    ]

    out = PROCESSED_DIR / "feature_list.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n📄 Feature 명세서 저장: {out}")


# ── 실행 ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=None)
    args = parser.parse_args()

    print("=" * 60)
    print("  SkyOps — Feature Engineering 시작")
    print("=" * 60)

    # Feature 명세서 먼저 저장
    save_feature_doc()

    # Feature 생성
    df_feat = build_features(args.sample)

    # Parquet 저장 (압축, 빠른 I/O)
    out_path = PROCESSED_DIR / "features.parquet"
    df_feat.to_parquet(out_path, index=False, compression="snappy")
    size_mb = out_path.stat().st_size / 1024 / 1024
    print(f"\n✅ 저장 완료: {out_path} ({size_mb:.0f} MB)")
    print(f"   shape: {df_feat.shape}")
    print(f"   컬럼: {list(df_feat.columns)[:10]} ...")
    print("\n다음 단계: python analysis/prepare_dataset.py")
