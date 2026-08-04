"""Cached data access for the demo. All heavy CSVs are loaded once per session.

- data/test_predictions_2023.csv: LightGBM Poisson 백테스트 산출물 (train 2019-2022, test
  2023) — 06 관리자·검증 화면의 모델 성능 증빙에 사용한다.
- data/lightgbm_poisson_model.txt: 위 백테스트를 만든 것과 동일한, 실제 학습된 LightGBM
  Poisson 부스터 원본 (train 2019-2022). 01 상황판의 "예측"은 이 모델을 그대로 불러와
  추론한다 — 근사치가 아니다.
- data/realtime_sample_2024.csv: 2024년 임의(합성) 실시간 신고 스트림. 01 상황판의 "실제"
  값과, 위 모델에 넣을 특성(직전 관측값 기반 lag/rolling/과거평균) 모두 이 파일 하나로만
  계산한다 — 예측 시점 이후의 값은 특성 계산에 전혀 쓰지 않는다(shift(1) 이후 계산).
- lightgbm 임포트/네이티브 라이브러리 로드가 실패하는 환경(예: Homebrew 없는 로컬 macOS)
  에서는 원 모델의 상위 2개 특성(rolling_mean_56 + historical_same_slot_mean, 전체
  중요도의 약 72%)만으로 근사하는 폴백을 사용한다 — Streamlit Cloud(Linux)에서는 실제
  모델이 로드되어 이 폴백은 쓰이지 않는 것이 정상이다.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"

REGION_SHORT = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천",
    "광주광역시": "광주", "대전광역시": "대전", "울산광역시": "울산", "세종특별자치시": "세종",
    "경기도": "경기", "강원도": "강원", "충청북도": "충북", "충청남도": "충남",
    "전라북도": "전북", "전라남도": "전남", "경상북도": "경북", "경상남도": "경남",
    "제주특별자치도": "제주",
}
REGION_ORDER = list(REGION_SHORT.keys())
SLOTS = [0, 3, 6, 9, 12, 15, 18, 21]

# 시도 중심 좌표 근사값 — 지도 마커 표시용.
REGION_COORDS = {
    "서울특별시": (37.5665, 126.9780),
    "부산광역시": (35.1796, 129.0756),
    "대구광역시": (35.8714, 128.6014),
    "인천광역시": (37.4563, 126.7052),
    "광주광역시": (35.1595, 126.8526),
    "대전광역시": (36.3504, 127.3845),
    "울산광역시": (35.5384, 129.3114),
    "세종특별자치시": (36.4800, 127.2890),
    "경기도": (37.4138, 127.5183),
    "강원도": (37.8228, 128.1555),
    "충청북도": (36.6357, 127.4917),
    "충청남도": (36.5184, 126.8000),
    "전라북도": (35.7175, 127.1530),
    "전라남도": (34.8161, 126.4629),
    "경상북도": (36.4919, 128.8889),
    "경상남도": (35.4606, 128.2132),
    "제주특별자치도": (33.4996, 126.5312),
}

CATEGORY_LABELS = {
    "약물과다": "약물과다",
    "약물중독": "약물중독",
    "약물오용": "약물오용",
    "약물부작용": "약물부작용",
    "마약중독": "마약중독",
    "의료용물질이아닌약물중독": "비의료용물질중독",
    "약물유발성 근육긴장 이상": "약물유발성 근긴장이상",
}


@st.cache_data(show_spinner=False)
def load_predictions() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "test_predictions_2023.csv")
    df["time_block"] = pd.to_datetime(df["time_block"])
    df["month_day"] = df["time_block"].dt.strftime("%m-%d")
    df["slot"] = df["time_block"].dt.hour
    return df


@st.cache_data(show_spinner=False)
def load_realtime() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "realtime_sample_2024.csv")
    df["time_block_start"] = pd.to_datetime(df["time_block_start"])
    df["event_time"] = pd.to_datetime(df["event_time"])
    df["month_day"] = df["time_block_start"].dt.strftime("%m-%d")
    df["slot"] = df["time_block_start"].dt.hour
    return df


ROLLING_SLOTS = 56  # 7일치 3시간 슬롯 수
ROLLING_MIN_PERIODS = 14  # 최소 1.75일치 확보되면 이동평균 사용
ROLLING_WEIGHT = 0.6
HISTORICAL_WEIGHT = 0.4

LGB_MODEL_PATH = DATA_DIR / "lightgbm_poisson_model.txt"
PERIODS_PER_DAY = 8
PERIODS_PER_WEEK = 56
LAG_SLOTS = [1, 2, 8, 16, 56, 112]
# run_metadata.json의 "features"와 동일한 순서 — 학습 스크립트 add_features()를 그대로 이식.
LGB_FEATURE_ORDER = [
    "region", "month", "dow", "slot", "quarter", "is_weekend", "days_since_start",
    "slot_sin", "slot_cos", "dow_sin", "dow_cos", "doy_sin", "doy_cos",
    *[f"lag_{lag}" for lag in LAG_SLOTS],
    "rolling_mean_8", "rolling_mean_56", "rolling_std_56",
    "historical_region_mean", "historical_same_slot_mean",
]


@st.cache_resource(show_spinner=False)
def _load_lgb_booster():
    import lightgbm as lgb  # 로컬(Homebrew 없는 macOS)에서는 libomp 부재로 임포트 자체가 실패할 수 있음

    return lgb.Booster(model_file=str(LGB_MODEL_PATH))


def _build_lgb_features(panel: pd.DataFrame) -> pd.DataFrame:
    """학습 스크립트의 add_features()와 동일한 24개 특성을 causal(shift(1) 이후)하게 구성한다.
    "slot"은 원 모델 기준 시간대 인덱스(0~7, hour//3)이며, 앱 전역에서 쓰는
    panel["slot"](=hour 값 0,3,...,21)과는 다른 이름 충돌을 피하기 위해 별도 프레임에서만 쓴다."""
    p = panel[["region", "time_block", "y"]].sort_values(["region", "time_block"]).reset_index(drop=True)
    ts = p["time_block"]

    p["month"] = ts.dt.month
    p["dow"] = ts.dt.dayofweek
    p["quarter"] = ts.dt.quarter
    p["is_weekend"] = (p["dow"] >= 5).astype(int)
    p["dayofyear"] = ts.dt.dayofyear
    p["slot"] = (ts.dt.hour // 3).astype(int)
    p["days_since_start"] = (ts - pd.Timestamp("2019-01-01")).dt.days

    p["slot_sin"] = np.sin(2 * np.pi * p["slot"] / PERIODS_PER_DAY)
    p["slot_cos"] = np.cos(2 * np.pi * p["slot"] / PERIODS_PER_DAY)
    p["dow_sin"] = np.sin(2 * np.pi * p["dow"] / 7)
    p["dow_cos"] = np.cos(2 * np.pi * p["dow"] / 7)
    p["doy_sin"] = np.sin(2 * np.pi * p["dayofyear"] / 365.25)
    p["doy_cos"] = np.cos(2 * np.pi * p["dayofyear"] / 365.25)

    group = p.groupby("region", sort=False, observed=True)["y"]
    for lag in LAG_SLOTS:
        p[f"lag_{lag}"] = group.shift(lag)
    p["rolling_mean_8"] = group.transform(lambda s: s.shift(1).rolling(8, min_periods=2).mean())
    p["rolling_mean_56"] = group.transform(lambda s: s.shift(1).rolling(56, min_periods=8).mean())
    p["rolling_std_56"] = group.transform(lambda s: s.shift(1).rolling(56, min_periods=8).std())
    p["historical_region_mean"] = group.transform(lambda s: s.shift(1).expanding(min_periods=8).mean())
    p["historical_same_slot_mean"] = p.groupby(
        ["region", "dow", "slot"], sort=False, observed=True
    )["y"].transform(lambda s: s.shift(1).expanding(min_periods=1).mean())

    # 연초(첫 2주) 등 lag_112까지 쌓이지 않은 구간 — 학습 스크립트는 이런 행을 통째로
    # dropna()하지만, 상황판은 연중 아무 날짜나 고를 수 있어야 하므로 0으로 채워 대체한다.
    numeric_cols = [c for c in LGB_FEATURE_ORDER if c != "region"]
    X = p[LGB_FEATURE_ORDER].copy()
    X[numeric_cols] = X[numeric_cols].fillna(0.0)
    X["region"] = X["region"].astype("category")
    return X


def _fallback_blend_prediction(panel: pd.DataFrame) -> pd.Series:
    """lightgbm을 쓸 수 없는 환경(로컬 macOS 등)을 위한 근사 — 원 모델 상위 2개 특성만 결합."""
    group = panel.groupby("region", sort=False, observed=True)["y"]
    rolling_mean_56 = group.transform(
        lambda s: s.shift(1).rolling(ROLLING_SLOTS, min_periods=ROLLING_MIN_PERIODS).mean()
    )
    historical_same_slot_mean = panel.groupby(
        ["region", "dow", "slot"], sort=False, observed=True
    )["y"].transform(lambda s: s.shift(1).expanding(min_periods=1).mean())
    overall_region_mean = group.transform("mean")

    has_roll = rolling_mean_56.notna()
    has_hist = historical_same_slot_mean.notna()
    blended = ROLLING_WEIGHT * rolling_mean_56.fillna(0) + HISTORICAL_WEIGHT * historical_same_slot_mean.fillna(0)

    prediction = pd.Series(overall_region_mean.to_numpy(), index=panel.index, dtype=float)
    prediction[has_roll & ~has_hist] = rolling_mean_56[has_roll & ~has_hist]
    prediction[has_hist & ~has_roll] = historical_same_slot_mean[has_hist & ~has_roll]
    prediction[has_roll & has_hist] = blended[has_roll & has_hist]
    return prediction.clip(lower=0)


@st.cache_data(show_spinner=False)
def load_2024_panel() -> pd.DataFrame:
    """2024 합성 실시간 샘플을 지역×3시간 슬롯 격자로 집계하고, 실제 학습된 LightGBM 모델로
    그 시점까지의 데이터만 사용한(causal) 예측치를 계산한다. "prediction_source" 컬럼은
    실제 어느 쪽으로 계산됐는지("lightgbm" 또는 "fallback_blend")를 모든 행에 동일하게 담는다."""
    rt = load_realtime()
    counts = (
        rt.groupby(["region", "time_block_start"], observed=True)
        .size()
        .rename("y")
        .reset_index()
    )

    full_year = pd.date_range("2024-01-01 00:00:00", "2024-12-31 21:00:00", freq="3h")
    grid = pd.MultiIndex.from_product([REGION_ORDER, full_year], names=["region", "time_block"]).to_frame(index=False)
    panel = grid.merge(counts, left_on=["region", "time_block"], right_on=["region", "time_block_start"], how="left")
    panel["y"] = panel["y"].fillna(0).astype(int)
    panel = panel.drop(columns=["time_block_start"]).sort_values(["region", "time_block"]).reset_index(drop=True)

    panel["dow"] = panel["time_block"].dt.dayofweek
    panel["slot"] = panel["time_block"].dt.hour
    panel["month_day"] = panel["time_block"].dt.strftime("%m-%d")

    try:
        X = _build_lgb_features(panel)
        booster = _load_lgb_booster()
        raw_pred = booster.predict(X)
        panel["prediction"] = np.clip(raw_pred, 1e-6, None)
        panel["prediction_source"] = "lightgbm"
    except Exception:
        panel["prediction"] = _fallback_blend_prediction(panel)
        panel["prediction_source"] = "fallback_blend"

    return panel


@st.cache_data(show_spinner=False)
def load_metrics() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "metrics.csv")


@st.cache_data(show_spinner=False)
def load_feature_importance() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "feature_importance.csv")


@st.cache_data(show_spinner=False)
def load_run_metadata() -> dict:
    return json.loads((DATA_DIR / "run_metadata.json").read_text())


@st.cache_data(show_spinner=False)
def load_province_geojson() -> dict:
    """시도 경계 GeoJSON (통계청 2018, southkorea/southkorea-maps 공개 데이터 기반).
    17개 시도 폴리곤을 지도 렌더링 부담을 줄이기 위해 단순화(simplify)해 미리 저장해둔 것."""
    return json.loads((DATA_DIR / "skorea_provinces_simple.geojson").read_text(encoding="utf-8"))


def national_day_series(month_day: str) -> pd.DataFrame:
    """예측·실제 전국 합계, 3시간 슬롯별 — 둘 다 2024 합성 스트림 하나로만 계산."""
    panel = load_2024_panel()
    pred_day = panel[panel["month_day"] == month_day].groupby("slot", as_index=False)["prediction"].sum()

    rt = load_realtime()
    rt_day = rt[rt["month_day"] == month_day]
    actual_day = rt_day.groupby("slot").size().reindex(SLOTS, fill_value=0).reset_index()
    actual_day.columns = ["slot", "actual"]

    out = pd.DataFrame({"slot": SLOTS})
    out = out.merge(pred_day, on="slot", how="left").merge(actual_day, on="slot", how="left")
    out["prediction"] = out["prediction"].fillna(0.0)
    out["actual"] = out["actual"].fillna(0)
    return out


def region_day_snapshot(month_day: str, up_to_slot: int) -> pd.DataFrame:
    """지역별: 지금까지(up_to_slot 포함) 실제 누적, 향후 예상(남은 슬롯 예측 합), 평시 대비 배수."""
    panel = load_2024_panel()
    pred_day = panel[panel["month_day"] == month_day]

    rt = load_realtime()
    rt_day = rt[rt["month_day"] == month_day]

    rows = []
    for region in REGION_ORDER:
        p_region = pred_day[pred_day["region"] == region]
        r_region = rt_day[rt_day["region"] == region]

        so_far_actual = int((r_region["slot"] <= up_to_slot).sum())
        so_far_pred = p_region[p_region["slot"] <= up_to_slot]["prediction"].sum()
        remaining_pred = p_region[p_region["slot"] > up_to_slot]["prediction"].sum()

        baseline = p_region["prediction"].mean() * len(SLOTS[: SLOTS.index(up_to_slot) + 1])
        ratio = so_far_actual / baseline if baseline > 0 else (1.0 if so_far_actual == 0 else 3.0)

        rows.append(
            {
                "region": region,
                "region_short": REGION_SHORT[region],
                "actual_so_far": so_far_actual,
                "predicted_so_far": round(float(so_far_pred), 1),
                "predicted_remaining": round(float(remaining_pred), 1),
                "ratio_vs_baseline": round(float(ratio), 2),
            }
        )
    return pd.DataFrame(rows)


def risk_level(ratio: float) -> str:
    if ratio >= 2.5:
        return "심각"
    if ratio >= 1.5:
        return "경계"
    if ratio >= 1.1:
        return "주의"
    return "관심"


def category_mix(month_day: str, up_to_slot: int) -> pd.DataFrame:
    rt = load_realtime()
    day = rt[(rt["month_day"] == month_day) & (rt["slot"] <= up_to_slot)]
    if day.empty:
        return pd.DataFrame(columns=["main_symptom", "count"])
    counts = day["main_symptom"].value_counts().reset_index()
    counts.columns = ["main_symptom", "count"]
    counts["label"] = counts["main_symptom"].map(CATEGORY_LABELS).fillna(counts["main_symptom"])
    return counts
