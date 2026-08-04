from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from .schemas import ExtractedFacts, LLMAnalysis, ProtocolResult, SourceHit


ACTION_LIBRARY: dict[str, str] = {
    "CONFIRM_LOCATION_PHONE": (
        "환자가 있는 정확한 위치와 다시 연락 가능한 전화번호를 먼저 확인합니다."
    ),
    "SEND_AMBULANCE_KEEP_LINE": (
        "구급차를 출동시키고, 신고자에게 전화를 끊지 말고 안내를 따르도록 말합니다."
    ),
    "ASK_CONSCIOUSNESS": (
        "환자에게 큰 소리로 불러 반응하거나 눈을 뜨는지 확인해 달라고 질문합니다."
    ),
    "ASK_NORMAL_BREATHING": (
        "가슴이 규칙적으로 오르내리는 정상 호흡이 있는지 확인합니다. "
        "헐떡임·불규칙한 숨·코고는 듯한 소리는 정상 호흡으로 단정하지 않습니다."
    ),
    "CPR_AED": (
        "의식이 없고 정상 호흡이 없으면 즉시 심정지 안내 프로토콜로 전환하여 "
        "심폐소생술과 자동심장충격기 안내를 시행합니다."
    ),
    "RECOVERY_POSITION_IF_SAFE": (
        "외상이 의심되지 않고 환자가 숨은 쉬지만 의식이 없으면, "
        "기도가 막히지 않도록 옆으로 눕혀 호흡을 계속 관찰하게 합니다."
    ),
    "SUPPORT_BREATHING": (
        "호흡이 느리거나 얕거나 불규칙하면 호흡상태를 계속 확인하고, "
        "호흡이 멈추면 즉시 심정지 안내로 전환합니다."
    ),
    "NALOXONE_LOCAL_POLICY_ONLY": (
        "오피오이드 과량복용이 의심되고 신고자가 날록손을 보유한 경우에는 "
        "기관의 승인된 신고자 날록손 안내 절차와 제품 표시사항에 따라서만 사용을 안내합니다. "
        "날록손 안내가 심폐소생술이나 호흡 보조를 지연시키면 안 됩니다."
    ),
    "ASK_DRUG_DETAILS": (
        "약물·물질명, 노출 경로, 노출 시각, 추정량, 구토 여부와 시각, "
        "증상 시작 시각, 다른 약·술의 동시 복용, 복용 의도를 확인합니다."
    ),
    "PRESERVE_CONTAINER": (
        "빈 약통·포장·처방전·설명서가 있으면 버리지 말고 구급대원에게 보여주도록 안내합니다."
    ),
    "DO_NOT_INDUCE_VOMITING": (
        "억지로 토하게 하지 않습니다. 스스로 토하면 기도로 넘어가지 않도록 고개를 옆으로 돌립니다."
    ),
    "SCENE_SAFETY_PPE": (
        "분말·농약·가스·주사침·오염된 의복·폭력 위험이 있으면 접근하지 말고 거리를 둡니다. "
        "신고자와 주변인의 2차 노출을 막습니다."
    ),
    "REMOVE_EXPOSURE_IF_SAFE": (
        "흡입 노출은 본인의 안전이 확보되는 범위에서만 신선한 공기가 있는 곳으로 이동합니다."
    ),
    "SKIN_DECONTAMINATION": (
        "피부나 의복에 독성 물질이 묻었으면 맨손 접촉을 피하고 오염된 의복을 벗긴 뒤 "
        "많은 물로 씻습니다."
    ),
    "AGITATION_DEESCALATION": (
        "환자를 자극하거나 제압하려 하지 말고, 거리를 유지하며 주변 사람과 위험 물건을 치웁니다."
    ),
    "REQUEST_POLICE_IF_THREAT": (
        "무기·폭력·자살 현장 또는 범죄 가능성이 있으면 경찰 공동대응을 요청합니다."
    ),
    "COOL_ENVIRONMENT": (
        "심한 흥분·발한·고체온이 의심되면 안전한 범위에서 서늘한 환경을 만들고 "
        "두꺼운 겉옷을 느슨하게 합니다."
    ),
    "ANAPHYLAXIS_BRANCH": (
        "얼굴·혀가 붓거나 침을 삼키지 못함, 쌕쌕거림, 호흡곤란, 실신이 있으면 "
        "아나필락시스 중증응급 프로토콜로 전환합니다."
    ),
    "DYSTONIA_AIRWAY_CHECK": (
        "목·턱·혀·눈이 비정상적으로 돌아가거나 굳는 경우 기도와 호흡, 삼킴 가능 여부를 우선 확인합니다. "
        "목이나 턱을 억지로 펴지 않습니다."
    ),
}


RED_KEYWORDS = [
    "청색증", "입술이 파래", "입술이 퍼래", "경련", "발작",
    "숨을 못", "호흡곤란", "숨이 멈", "무호흡",
    "얼굴이 붓", "혀가 붓", "침을 못 삼", "의식을 잃",
    "쓰러져", "가슴 통증", "흉통",
]

AGITATION_KEYWORDS = [
    "난폭", "폭력", "위협", "칼", "흉기", "총", "깨부수", "날뛰",
    "극심한 흥분", "환각", "망상",
]

CHEMICAL_KEYWORDS = [
    "농약", "제초제", "살충제", "부식제", "락스", "염산", "가스",
    "일산화탄소", "분말", "화학물질", "세제", "시안",
]

OPIOID_KEYWORDS = [
    "헤로인", "펜타닐", "모르핀", "옥시코돈", "코데인", "아편",
    "마약성 진통제", "날록손", "나르칸",
]

STIMULANT_KEYWORDS = [
    "필로폰", "메스암페타민", "암페타민", "코카인", "엑스터시",
]

DYSTONIA_KEYWORDS = [
    "근육긴장", "근긴장", "목이 돌아", "턱이 굳", "혀가 돌아",
    "눈이 위로", "안구편위", "몸이 비틀", "근육이 굳",
]


@dataclass
class HardSignal:
    conscious: bool | None
    normal_breathing: bool | None
    symptoms: list[str]
    hazards: list[str]


def _contains_any(text: str, words: Iterable[str]) -> bool:
    return any(word in text for word in words)


def extract_hard_signals(transcript: str) -> HardSignal:
    text = re.sub(r"\s+", " ", transcript)

    conscious: bool | None = None
    if re.search(r"(의식|반응).{0,8}(없|안\s*하|없어|없고)|깨우.{0,5}(안|못)", text):
        conscious = False
    elif re.search(r"(의식|반응).{0,8}(있|하고)|대답.{0,5}(해|함)|말은\s*해", text):
        conscious = True

    normal_breathing: bool | None = None
    if re.search(
        r"(숨|호흡).{0,8}(안\s*쉬|쉬지|없|멈|못\s*쉬)|무호흡|"
        r"숨.{0,8}(느리|얕|불규칙)|헐떡|코고는.{0,8}(소리|숨)|가글",
        text,
    ):
        normal_breathing = False
    elif re.search(r"정상.{0,5}(호흡|숨)|숨은\s*정상|호흡은\s*정상", text):
        normal_breathing = True

    symptoms: list[str] = []
    for word in RED_KEYWORDS + [
        "구토", "졸림", "의식저하", "축동", "동공이 작",
        "발한", "고열", "고체온", "심계항진", "침을 흘",
        "근육 연축",
    ]:
        if word in text:
            symptoms.append(word)

    hazards: list[str] = []
    for word in AGITATION_KEYWORDS + CHEMICAL_KEYWORDS + ["주사침", "바늘", "유서"]:
        if word in text:
            hazards.append(word)

    return HardSignal(
        conscious=conscious,
        normal_breathing=normal_breathing,
        symptoms=list(dict.fromkeys(symptoms)),
        hazards=list(dict.fromkeys(hazards)),
    )


def merge_facts(
    transcript: str,
    llm_analysis: LLMAnalysis | None,
) -> ExtractedFacts:
    hard = extract_hard_signals(transcript)
    facts = llm_analysis.facts if llm_analysis else ExtractedFacts()

    # 의식·호흡은 안전 핵심값이므로 규칙에서 명시적으로 포착된 값이 있으면 우선합니다.
    if hard.conscious is not None:
        facts.conscious = hard.conscious
    if hard.normal_breathing is not None:
        facts.normal_breathing = hard.normal_breathing

    facts.symptoms = list(dict.fromkeys(facts.symptoms + hard.symptoms))
    facts.scene_hazards = list(dict.fromkeys(facts.scene_hazards + hard.hazards))
    return facts


def infer_category(transcript: str, llm_analysis: LLMAnalysis | None) -> str:
    text = transcript
    if _contains_any(text, DYSTONIA_KEYWORDS):
        return "약물유발성 근육긴장 이상"
    if _contains_any(text, CHEMICAL_KEYWORDS):
        return "의료용물질이아닌약물중독"
    if _contains_any(text, OPIOID_KEYWORDS):
        return "마약중독"
    if "부작용" in text or "알레르기" in text or "아나필락시스" in text:
        return "약물부작용"
    if "과다" in text or "많이 먹" in text or "한꺼번에" in text:
        return "약물과다"
    if "잘못 먹" in text or "중복 복용" in text or "용법" in text:
        return "약물오용"
    if llm_analysis:
        return llm_analysis.category
    return "약물중독" if "약" in text or "마약" in text else "미상"


def infer_toxidrome(transcript: str, llm_analysis: LLMAnalysis | None) -> str:
    if _contains_any(transcript, DYSTONIA_KEYWORDS):
        return "급성 근긴장이상"
    if _contains_any(transcript, OPIOID_KEYWORDS) or (
        ("동공" in transcript or "축동" in transcript)
        and ("호흡" in transcript or "숨" in transcript)
    ):
        return "오피오이드성"
    if _contains_any(transcript, STIMULANT_KEYWORDS) or (
        ("흥분" in transcript or "발한" in transcript)
        and ("고열" in transcript or "가슴 통증" in transcript)
    ):
        return "교감신경흥분성"
    if _contains_any(transcript, CHEMICAL_KEYWORDS):
        return "부식성/화학물질"
    return llm_analysis.suspected_toxidrome if llm_analysis else "혼합/미상"


def determine_urgency(transcript: str, facts: ExtractedFacts) -> str:
    text = transcript

    if facts.conscious is False and facts.normal_breathing is False:
        return "RED"

    severe_airway = _contains_any(
        text,
        ["청색증", "입술이 파래", "숨을 못", "무호흡", "혀가 붓", "침을 못 삼"],
    )
    active_seizure = _contains_any(text, ["경련 중", "계속 경련", "발작 중"])
    violent_scene = bool(facts.scene_hazards) and _contains_any(text, AGITATION_KEYWORDS)
    stimulant_chest_pain = _contains_any(text, STIMULANT_KEYWORDS) and _contains_any(
        text, ["가슴 통증", "흉통", "심장이 너무 빨리", "심계항진"]
    )

    if severe_airway or active_seizure or violent_scene or stimulant_chest_pain:
        return "RED"

    if (
        facts.conscious is False
        or facts.normal_breathing is False
        or facts.intent == "자살/자해"
        or _contains_any(text, CHEMICAL_KEYWORDS)
        or _contains_any(text, ["의식저하", "심한 졸림", "고체온", "계속 토"])
    ):
        return "ORANGE"

    if facts.conscious is True and facts.normal_breathing is True:
        return "YELLOW"

    return "UNKNOWN"


def build_action_ids(
    transcript: str,
    facts: ExtractedFacts,
    urgency: str,
    llm_analysis: LLMAnalysis | None,
) -> list[str]:
    text = transcript
    actions = ["CONFIRM_LOCATION_PHONE", "SEND_AMBULANCE_KEEP_LINE"]

    if facts.conscious is None:
        actions.append("ASK_CONSCIOUSNESS")
    if facts.normal_breathing is None:
        actions.append("ASK_NORMAL_BREATHING")

    if facts.conscious is False and facts.normal_breathing is False:
        actions.append("CPR_AED")
        if _contains_any(text, OPIOID_KEYWORDS) or "날록손" in text:
            actions.append("NALOXONE_LOCAL_POLICY_ONLY")
    elif facts.conscious is False and facts.normal_breathing is not False:
        actions.extend(["RECOVERY_POSITION_IF_SAFE", "SUPPORT_BREATHING"])
    elif facts.normal_breathing is False:
        actions.append("SUPPORT_BREATHING")

    if _contains_any(text, OPIOID_KEYWORDS):
        actions.append("NALOXONE_LOCAL_POLICY_ONLY")

    actions.extend(["ASK_DRUG_DETAILS", "PRESERVE_CONTAINER"])

    if _contains_any(text, ["먹", "삼켰", "복용", "섭취", "구토"]):
        actions.append("DO_NOT_INDUCE_VOMITING")

    if _contains_any(text, CHEMICAL_KEYWORDS):
        actions.extend(
            ["SCENE_SAFETY_PPE", "REMOVE_EXPOSURE_IF_SAFE", "SKIN_DECONTAMINATION"]
        )

    if _contains_any(text, AGITATION_KEYWORDS + STIMULANT_KEYWORDS):
        actions.extend(
            ["AGITATION_DEESCALATION", "REQUEST_POLICE_IF_THREAT", "COOL_ENVIRONMENT"]
        )

    if _contains_any(text, ["얼굴이 붓", "혀가 붓", "침을 못 삼", "쌕쌕", "아나필락시스"]):
        actions.append("ANAPHYLAXIS_BRANCH")

    if _contains_any(text, DYSTONIA_KEYWORDS):
        actions.append("DYSTONIA_AIRWAY_CHECK")

    # LLM이 제안하더라도 사전 승인된 action ID만 허용합니다.
    if llm_analysis:
        actions.extend(
            action_id
            for action_id in llm_analysis.recommended_action_ids
            if action_id in ACTION_LIBRARY
        )

    return list(dict.fromkeys(actions))


def build_next_questions(facts: ExtractedFacts, llm_analysis: LLMAnalysis | None) -> list[str]:
    questions: list[str] = []
    if not facts.location:
        questions.append("환자가 있는 정확한 주소 또는 위치는 어디입니까?")
    if not facts.callback_number:
        questions.append("전화가 끊길 경우 다시 연락할 번호가 어떻게 됩니까?")
    if facts.conscious is None:
        questions.append("환자에게 큰 소리로 불렀을 때 반응하거나 눈을 뜹니까?")
    if facts.normal_breathing is None:
        questions.append("환자의 가슴이 규칙적으로 오르내리는 정상 호흡이 있습니까?")
    if not facts.suspected_substance:
        questions.append("무슨 약이나 물질입니까? 약통·포장지에 적힌 이름을 읽어주세요.")
    if not facts.route:
        questions.append("먹었습니까, 흡입했습니까, 주사했습니까, 피부나 눈에 묻었습니까?")
    if not facts.exposure_time:
        questions.append("언제 노출되거나 복용했습니까?")
    if not facts.amount:
        questions.append("얼마나 복용하거나 노출되었습니까? 남은 약 개수도 확인해 주세요.")
    if facts.vomiting is None:
        questions.append("복용 후 토했습니까? 토했다면 언제입니까?")
    if facts.intent == "미상":
        questions.append("사고로 복용했습니까, 일부러 복용했습니까?")
    questions.append("술이나 다른 약을 함께 복용했습니까?")
    questions.append("경련, 심한 졸림, 호흡곤란, 얼굴·혀 부종, 가슴 통증, 심한 흥분이 있습니까?")

    if llm_analysis:
        questions.extend(llm_analysis.next_questions)

    return list(dict.fromkeys(questions))[:8]


def make_dispatch_recommendation(urgency: str, transcript: str) -> str:
    if urgency == "RED":
        if _contains_any(transcript, AGITATION_KEYWORDS):
            return "즉시 구급 출동 + 현장안전을 위한 경찰 공동대응 검토 + 전문상담 연결"
        return "즉시 구급 출동 + 심정지/중증응급 전문상담 즉시 연결"
    if urgency == "ORANGE":
        return "긴급 구급 출동 + 구급상황관리사/의료지도 연결 검토"
    if urgency == "YELLOW":
        return "구급 출동 및 지속 재평가; 증상 악화 시 즉시 RED/ORANGE로 상향"
    return "구급 출동을 우선하고, 의식·정상호흡을 확인할 때까지 중증도 미확정으로 관리"


def build_field_handoff(category: str, facts: ExtractedFacts, urgency: str) -> str:
    def value(x: object) -> str:
        if x is None or x == [] or x == "":
            return "미확인"
        if isinstance(x, list):
            return ", ".join(map(str, x)) or "미확인"
        return str(x)

    return (
        f"[{urgency}/{category}] "
        f"위치 {value(facts.location)}, 환자 {value(facts.age)} {value(facts.sex)}, "
        f"의식 {value(facts.conscious)}, 정상호흡 {value(facts.normal_breathing)}, "
        f"의심물질 {value(facts.suspected_substance)}, 경로 {value(facts.route)}, "
        f"추정량 {value(facts.amount)}, 노출시각 {value(facts.exposure_time)}, "
        f"증상 {value(facts.symptoms)}, 의도 {value(facts.intent)}, "
        f"현장위험 {value(facts.scene_hazards)}."
    )


def build_protocol(
    transcript: str,
    llm_analysis: LLMAnalysis | None,
    source_hits: list[SourceHit],
) -> ProtocolResult:
    facts = merge_facts(transcript, llm_analysis)
    category = infer_category(transcript, llm_analysis)
    toxidrome = infer_toxidrome(transcript, llm_analysis)
    urgency = determine_urgency(transcript, facts)
    action_ids = build_action_ids(transcript, facts, urgency, llm_analysis)

    instructions = [ACTION_LIBRARY[action_id] for action_id in action_ids]
    do_not = []
    if "DO_NOT_INDUCE_VOMITING" in action_ids:
        do_not.append("억지로 토하게 하지 않기")
    if "SCENE_SAFETY_PPE" in action_ids:
        do_not.append("분말·농약·가스·주사침·오염물질에 맨손으로 접근하지 않기")
    if "AGITATION_DEESCALATION" in action_ids:
        do_not.append("폭력 가능 환자를 신고자가 직접 제압하거나 논쟁하지 않기")
    do_not.extend(
        [
            "LLM이 제시한 약물 용량을 현장지침·의료지도 확인 없이 사용하지 않기",
            "환자가 잠들었다고 단순 주취로 판단하지 않기",
        ]
    )

    warnings = [
        "이 결과는 상황요원의 판단을 보조하는 MVP이며 공식 지침이나 의료지도를 대체하지 않습니다.",
        "한국 119 표준지침과 지역 지침을 우선하고, 해외 지침은 보조 근거로만 사용합니다.",
        "날록손 신고자 안내는 기관이 승인한 별도 절차가 있을 때만 활성화해야 합니다.",
    ]

    return ProtocolResult(
        category=category,
        suspected_toxidrome=toxidrome,
        urgency=urgency,
        dispatch_recommendation=make_dispatch_recommendation(urgency, transcript),
        caller_instructions=instructions,
        next_questions=build_next_questions(facts, llm_analysis),
        do_not=list(dict.fromkeys(do_not)),
        field_handoff=build_field_handoff(category, facts, urgency),
        source_hits=source_hits,
        facts=facts,
        warnings=warnings,
    )
