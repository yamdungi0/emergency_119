from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


DrugCategory = Literal[
    "마약중독",
    "약물과다",
    "약물부작용",
    "약물오용",
    "약물유발성 근육긴장 이상",
    "약물중독",
    "의료용물질이아닌약물중독",
    "미상",
]

Urgency = Literal["RED", "ORANGE", "YELLOW", "UNKNOWN"]


class ExtractedFacts(BaseModel):
    location: str | None = None
    callback_number: str | None = None
    age: str | None = None
    sex: str | None = None

    conscious: bool | None = None
    normal_breathing: bool | None = None

    suspected_substance: str | None = None
    route: str | None = None
    amount: str | None = None
    exposure_time: str | None = None
    vomiting: bool | None = None
    symptom_onset: str | None = None
    intent: Literal["사고", "오용", "자살/자해", "범죄", "미상"] = "미상"
    co_ingestants: list[str] = Field(default_factory=list)
    symptoms: list[str] = Field(default_factory=list)
    scene_hazards: list[str] = Field(default_factory=list)
    naloxone_available: bool | None = None
    package_available: bool | None = None

    # LLM이 뽑은 값은 반드시 원문 근거 문구를 같이 남깁니다.
    evidence_quotes: list[str] = Field(default_factory=list)


class LLMAnalysis(BaseModel):
    category: DrugCategory = "미상"
    suspected_toxidrome: Literal[
        "오피오이드성",
        "교감신경흥분성",
        "콜린성",
        "진정수면성",
        "알레르기/아나필락시스",
        "급성 근긴장이상",
        "부식성/화학물질",
        "저혈당성",
        "혼합/미상",
    ] = "혼합/미상"
    facts: ExtractedFacts
    recommended_action_ids: list[str] = Field(default_factory=list)
    next_questions: list[str] = Field(default_factory=list)
    rationale: str = ""
    uncertainty: list[str] = Field(default_factory=list)


class SourceHit(BaseModel):
    title: str
    page: int | None = None
    snippet: str
    score: float


class ProtocolResult(BaseModel):
    category: DrugCategory
    suspected_toxidrome: str
    urgency: Urgency
    dispatch_recommendation: str
    caller_instructions: list[str]
    next_questions: list[str]
    do_not: list[str]
    field_handoff: str
    source_hits: list[SourceHit]
    facts: ExtractedFacts
    warnings: list[str] = Field(default_factory=list)
