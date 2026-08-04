"""Cached data access for the demo. All heavy CSVs are loaded once per session.

Two real artifacts drive the "예측 vs 실제" story described in the project brief:
- data/test_predictions_2023.csv: LightGBM Poisson 백테스트 (train 2019-2022, test 2023).
- data/realtime_sample_2024.csv: 2024년 임의(합성) 실시간 신고 스트림 — 아직 실제 데이터가
  쌓이기 전, "예측이 실시간으로 들어오는 데이터로 갱신되는" 흐름을 보여주기 위한 자리표시자.
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


@st.cache_data(show_spinner=False)
def load_metrics() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "metrics.csv")


@st.cache_data(show_spinner=False)
def load_feature_importance() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "feature_importance.csv")


@st.cache_data(show_spinner=False)
def load_run_metadata() -> dict:
    return json.loads((DATA_DIR / "run_metadata.json").read_text())


def demo_day_options() -> list[str]:
    return ["08-04", "01-13", "03-22", "05-31", "07-05", "10-18", "11-24", "12-31"]


def national_day_series(month_day: str) -> pd.DataFrame:
    """예측(2023) vs 실제(2024 합성) 전국 합계, 3시간 슬롯별."""
    pred = load_predictions()
    pred_day = pred[pred["month_day"] == month_day].groupby("slot", as_index=False)["prediction"].sum()

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
    pred = load_predictions()
    pred_day = pred[pred["month_day"] == month_day]

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
    return "정상"


def category_mix(month_day: str, up_to_slot: int) -> pd.DataFrame:
    rt = load_realtime()
    day = rt[(rt["month_day"] == month_day) & (rt["slot"] <= up_to_slot)]
    if day.empty:
        return pd.DataFrame(columns=["main_symptom", "count"])
    counts = day["main_symptom"].value_counts().reset_index()
    counts.columns = ["main_symptom", "count"]
    counts["label"] = counts["main_symptom"].map(CATEGORY_LABELS).fillna(counts["main_symptom"])
    return counts
