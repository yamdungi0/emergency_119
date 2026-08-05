from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


UnknownState = Literal["예", "아니오", "미상", "확인 필요"]
RouteState = Literal["경구", "흡입", "피부", "주사", "안구", "기타", "미상"]
ConsciousnessState = Literal["A", "V", "P", "U", "미상"]


class Evidence(BaseModel):
    """각 추출값의 원문 근거."""

    model_config = ConfigDict(extra="forbid")

    field: str
    quote: str
    source: Literal["통화", "현장소견", "활력징후", "규칙", "미상"]


class DrugExtraction(BaseModel):
    """LLM과 규칙 엔진이 공통으로 사용하는 고정 출력 스키마."""

    model_config = ConfigDict(extra="forbid")

    age_group: str | None = Field(
        default=None, description="예: 50대. 확인되지 않으면 null"
    )
    sex: Literal["남성", "여성", "미상"] = "미상"

    suspected_drug: str | None = Field(
        default=None, description="확인된 제품명 또는 통화에서 언급된 약물명"
    )
    drug_group: str | None = Field(
        default=None, description="예: 수면제·진정제. 근거가 없으면 null"
    )

    exposure_time_text: str | None = None
    exposure_minutes: int | None = Field(default=None, ge=0, le=10080)
    amount_text: str | None = None
    amount_exact: bool = False
    route: RouteState = "미상"

    consciousness: ConsciousnessState = "미상"
    respiratory_rate: int | None = Field(default=None, ge=0, le=100)
    spo2: int | None = Field(default=None, ge=0, le=100)

    alcohol_use: UnknownState = "미상"
    multiple_drug_use: UnknownState = "미상"
    suicide_risk: UnknownState = "확인 필요"
    medicine_container_secured: UnknownState = "미상"

    summary: str = Field(
        default="",
        description="입력에 존재하는 사실만 사용한 2문장 이내 요약",
    )
    evidence: list[Evidence] = Field(default_factory=list)
    extraction_notes: list[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    missing_required: list[str] = Field(default_factory=list)
    risk_alerts: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)


class ConfirmedCase(BaseModel):
    """사용자가 확인·수정한 최종 매핑값."""

    model_config = ConfigDict(extra="forbid")

    suspected_drug: str | None = None
    drug_group: str | None = None
    exposure_time_text: str | None = None
    amount_text: str | None = None
    route: RouteState = "미상"
    consciousness: ConsciousnessState = "미상"
    respiratory_rate: int | None = None
    spo2: int | None = None
    alcohol_use: UnknownState = "미상"
    multiple_drug_use: UnknownState = "미상"
    suicide_risk: UnknownState = "확인 필요"
    medicine_container_secured: UnknownState = "미상"
