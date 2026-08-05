"""국립중앙의료원 응급의료기관 정보 조회 서비스 연동(data.go.kr B552657/ErmctInfoInqireService).

검증 결과(2026-08-05):
- getEgytLcinfoInqire (위치기반 병원 목록): WGS84_LAT/WGS84_LON으로 정상 필터링됨.
- getEmrrmRltmUsefulSckbdInfoInqire (실시간 가용병상): HPID 파라미터가 서버단에서
  무시되고 전국 444곳이 그대로 반환되는 것을 확인했다. 그래서 병상 데이터는 전체
  목록을 한 번에 받아 hpid로 로컬 매칭한다 — 서버 측 단건 필터를 신뢰하지 않는다.

키가 없거나 호출이 실패하면 None을 반환한다. 호출부(pages/5)가 이 경우 샘플
데이터로 대체해야 한다.
"""

from __future__ import annotations

import json
import os
import urllib.request
from urllib.parse import urlencode

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BASE = "https://apis.data.go.kr/B552657/ErmctInfoInqireService"


def _call(op: str, params: dict, num_of_rows: int = 10) -> list[dict]:
    key = os.getenv("EMRMD_SERVICE_KEY", "").strip()
    if not key:
        raise RuntimeError("EMRMD_SERVICE_KEY가 설정되지 않았습니다.")
    qs = urlencode({**params, "numOfRows": num_of_rows, "pageNo": 1, "_type": "json"})
    url = f"{BASE}/{op}?serviceKey={key}&{qs}"
    with urllib.request.urlopen(url, timeout=10) as r:
        body = json.load(r)
    items = body.get("response", {}).get("body", {}).get("items", {}).get("item", [])
    return items if isinstance(items, list) else [items] if items else []


@st.cache_data(ttl=300, show_spinner=False)
def _nearby_hospitals_raw(lat: float, lon: float, n: int) -> list[dict]:
    return _call("getEgytLcinfoInqire", {"WGS84_LAT": lat, "WGS84_LON": lon}, n)


def nearby_hospitals(lat: float, lon: float, n: int = 10) -> list[dict] | None:
    """위경도 기준 가까운 응급의료기관 목록(거리순). 실패 시 None.
    성공한 결과만 캐시한다 — 실패까지 캐시하면 한 번의 일시적 오류로 몇 분간
    계속 샘플 데이터가 보이게 된다."""
    try:
        return _nearby_hospitals_raw(lat, lon, n)
    except Exception:
        return None


@st.cache_data(ttl=180, show_spinner=False)
def _all_bed_availability_raw() -> dict[str, dict]:
    items = _call("getEmrrmRltmUsefulSckbdInfoInqire", {}, num_of_rows=500)
    return {it["hpid"]: it for it in items if it.get("hpid")}


def all_bed_availability() -> dict[str, dict] | None:
    """전국 응급실 실시간 가용병상 정보 — hpid를 키로 하는 dict. 실패 시 None.
    성공한 결과만 캐시한다(위와 동일한 이유)."""
    try:
        return _all_bed_availability_raw()
    except Exception:
        return None
