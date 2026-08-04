"""Cached data access for the demo. All heavy CSVs are loaded once per session.

- data/test_predictions_2023.csv: LightGBM Poisson 백테스트 산출물 (train 2019-2022, test
  2023) — 06 관리자·검증 화면의 모델 성능 증빙에만 사용한다. 2023년은 학습·검증 도구일 뿐,
  01 상황판이 보여주는 "지금 시점 예측"의 근거가 아니다.
- data/realtime_sample_2024.csv: 2024년 임의(합성) 실시간 신고 스트림. 01 상황판의 "실제"와
  "예측" 모두 이 파일 하나로만 계산한다 — 예측은 같은 2024년 타임라인 안에서, 그 시점까지
  누적된 데이터만으로(미래를 보지 않고) 최근 7일 이동평균과 동일 요일·시간대 평균을 결합해
  구한다. 원 LightGBM 모델에서도 이 두 특성이 전체 중요도의 약 72%를 차지했다
  (feature_importance.csv: rolling_mean_56 + historical_same_slot_mean).
"""

from __future__ import annotations

import json
from pathlib import Path

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


@st.cache_data(show_spinner=False)
def load_2024_panel() -> pd.DataFrame:
    """2024 합성 실시간 샘플을 지역×3시간 슬롯 격자로 집계하고, 그 시점까지의 데이터만으로
    인과적(causal) 예측치를 계산한다. 미래 값을 보지 않도록 전부 shift(1) 이후 계산한다."""
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

    group = panel.groupby("region", sort=False, observed=True)["y"]
    panel["rolling_mean_56"] = group.transform(
        lambda s: s.shift(1).rolling(ROLLING_SLOTS, min_periods=ROLLING_MIN_PERIODS).mean()
    )
    panel["historical_same_slot_mean"] = panel.groupby(
        ["region", "dow", "slot"], sort=False, observed=True
    )["y"].transform(lambda s: s.shift(1).expanding(min_periods=1).mean())
    overall_region_mean = group.transform("mean")

    has_roll = panel["rolling_mean_56"].notna()
    has_hist = panel["historical_same_slot_mean"].notna()
    blended = ROLLING_WEIGHT * panel["rolling_mean_56"].fillna(0) + HISTORICAL_WEIGHT * panel["historical_same_slot_mean"].fillna(0)

    prediction = pd.Series(overall_region_mean.to_numpy(), index=panel.index, dtype=float)
    prediction[has_roll & ~has_hist] = panel.loc[has_roll & ~has_hist, "rolling_mean_56"]
    prediction[has_hist & ~has_roll] = panel.loc[has_hist & ~has_roll, "historical_same_slot_mean"]
    prediction[has_roll & has_hist] = blended[has_roll & has_hist]
    panel["prediction"] = prediction.clip(lower=0)
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
