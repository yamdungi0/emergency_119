from __future__ import annotations

import re
from dataclasses import dataclass

from drug_dictionary import DRUG_ALIASES
from models import DrugExtraction, Evidence, ValidationResult


KOREAN_NUMBERS = {
    "한": 1, "하나": 1, "두": 2, "둘": 2, "세": 3, "셋": 3,
    "네": 4, "넷": 4, "다섯": 5, "여섯": 6, "일곱": 7,
    "여덟": 8, "아홉": 9, "열": 10,
}


def normalize_text(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"\s+", " ", text)
    replacements = {
        "산소 포화도": "산소포화도",
        "에스피오투": "SpO2",
        "에스피오2": "SpO2",
        "호흡 수": "호흡수",
        "복용 시간": "복용시각",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _first_quote(text: str, pattern: str) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(0) if match else ""


def _extract_age_sex(text: str) -> tuple[str | None, str]:
    age_match = re.search(r"(\d{1,3})\s*대", text)
    age_group = f"{age_match.group(1)}대" if age_match else None

    if re.search(r"여성|여자|여환", text):
        sex = "여성"
    elif re.search(r"남성|남자|남환", text):
        sex = "남성"
    else:
        sex = "미상"
    return age_group, sex


def _extract_drug(text: str) -> tuple[str | None, str | None, str]:
    lowered = text.lower()
    for item in DRUG_ALIASES.values():
        for alias in item["aliases"]:
            if str(alias).lower() in lowered:
                return str(item["canonical"]), str(item["group"]), str(alias)
    return None, None, ""


def _extract_time(text: str) -> tuple[str | None, int | None, str]:
    minute = re.search(r"(\d{1,4})\s*분\s*(?:전|전에)", text)
    if minute:
        value = int(minute.group(1))
        return f"약 {value}분 전", value, minute.group(0)

    hour = re.search(r"(\d{1,3})\s*시간\s*(?:전|전에)", text)
    if hour:
        value = int(hour.group(1))
        return f"약 {value}시간 전", value * 60, hour.group(0)

    korean = re.search(
        r"(한|하나|두|둘|세|셋|네|넷)\s*시간\s*(?:전|전에)", text
    )
    if korean:
        value = KOREAN_NUMBERS[korean.group(1)]
        return f"약 {value}시간 전", value * 60, korean.group(0)

    clock = re.search(r"(?:오늘\s*)?(오전|오후)?\s*(\d{1,2})\s*시(?:\s*(\d{1,2})\s*분)?", text)
    if clock:
        return clock.group(0), None, clock.group(0)

    return None, None, ""


def _extract_amount(text: str) -> tuple[str | None, bool, str]:
    numeric = re.search(
        r"(\d{1,4})\s*(정|알|개|포|봉|병|통|캡슐)", text
    )
    if numeric:
        return f"{numeric.group(1)}{numeric.group(2)}", True, numeric.group(0)

    korean = re.search(
        r"(한|하나|두|둘|세|셋|네|넷)\s*(통|병|봉|포|알|정)", text
    )
    if korean:
        value = KOREAN_NUMBERS[korean.group(1)]
        unit = korean.group(2)
        # 용기 단위는 내부 정수량이 확인되지 않으므로 정확량이 아님.
        exact = unit in {"알", "정"}
        suffix = "" if exact else " 추정·정확량 미상"
        return f"{value}{unit}{suffix}", exact, korean.group(0)

    if re.search(r"전부|모두|남은 약", text):
        quote = _first_quote(text, r"(남은\s*약을\s*)?(전부|모두)")
        return "남은 약 전부·정확량 미상", False, quote

    return None, False, ""


def _extract_route(text: str) -> tuple[str, str]:
    patterns = {
        "경구": r"먹었|삼켰|복용|경구",
        "흡입": r"흡입|들이마셨|가스",
        "피부": r"피부|묻었|접촉",
        "주사": r"주사|정맥|근육",
        "안구": r"눈에|안구",
    }
    for route, pattern in patterns.items():
        quote = _first_quote(text, pattern)
        if quote:
            return route, quote
    return "미상", ""


def _extract_consciousness(text: str) -> tuple[str, str]:
    if re.search(r"의식\s*[=:]?\s*V\b|말하면\s*반응|음성에\s*반응", text, re.I):
        return "V", _first_quote(text, r"의식\s*[=:]?\s*V\b|말하면\s*반응|음성에\s*반응")
    if re.search(r"의식\s*[=:]?\s*A\b|명료|깨어\s*있", text, re.I):
        return "A", _first_quote(text, r"의식\s*[=:]?\s*A\b|명료|깨어\s*있")
    if re.search(r"의식\s*[=:]?\s*P\b|통증에\s*반응", text, re.I):
        return "P", _first_quote(text, r"의식\s*[=:]?\s*P\b|통증에\s*반응")
    if re.search(r"의식\s*[=:]?\s*U\b|반응\s*없|깨워도\s*(?:잘\s*)?반응하지", text, re.I):
        return "U", _first_quote(text, r"의식\s*[=:]?\s*U\b|반응\s*없|깨워도\s*(?:잘\s*)?반응하지")
    return "미상", ""


def _extract_vitals(text: str) -> tuple[int | None, int | None, list[Evidence]]:
    evidence: list[Evidence] = []
    rr = None
    spo2 = None

    rr_match = re.search(r"(?:호흡수|RR)\s*[:=]?\s*(\d{1,2})", text, re.I)
    if rr_match:
        rr = int(rr_match.group(1))
        evidence.append(Evidence(field="respiratory_rate", quote=rr_match.group(0), source="활력징후"))

    spo2_match = re.search(
        r"(?:SpO2|산소포화도)\s*[:=]?\s*(\d{1,3})\s*%?", text, re.I
    )
    if spo2_match:
        spo2 = int(spo2_match.group(1))
        evidence.append(Evidence(field="spo2", quote=spo2_match.group(0), source="활력징후"))

    return rr, spo2, evidence


def _state_from_patterns(
    text: str,
    positive: str,
    negative: str | None = None,
    uncertain: str | None = None,
) -> str:
    # "모르겠다", "확인 필요" 같은 불확실 표현을 양성으로 오판하지 않도록 우선 처리한다.
    if uncertain and re.search(uncertain, text):
        return "확인 필요"
    if negative and re.search(negative, text):
        return "아니오"
    if re.search(positive, text):
        return "예"
    return "미상"


def extract_with_rules(transcript: str, field_note: str, vital_text: str = "") -> DrugExtraction:
    transcript = normalize_text(transcript)
    field_note = normalize_text(field_note)
    vital_text = normalize_text(vital_text)
    combined = " ".join(part for part in [transcript, field_note, vital_text] if part)

    result = DrugExtraction()
    result.age_group, result.sex = _extract_age_sex(combined)

    drug, group, drug_quote = _extract_drug(combined)
    result.suspected_drug = drug
    result.drug_group = group
    if drug_quote:
        result.evidence.append(Evidence(field="suspected_drug", quote=drug_quote, source="규칙"))

    time_text, minutes, time_quote = _extract_time(combined)
    result.exposure_time_text = time_text
    result.exposure_minutes = minutes
    if time_quote:
        result.evidence.append(Evidence(field="exposure_time", quote=time_quote, source="규칙"))

    # 복용량은 통화 원문을 우선한다. 현장소견의 "빈 약통 1개 발견"을
    # 실제 복용량으로 오인하지 않도록 입력 출처를 분리한다.
    amount_text, amount_exact, amount_quote = _extract_amount(transcript)
    if amount_text is None:
        amount_text, amount_exact, amount_quote = _extract_amount(field_note)
    result.amount_text = amount_text
    result.amount_exact = amount_exact
    if amount_quote:
        result.evidence.append(Evidence(field="amount", quote=amount_quote, source="규칙"))

    result.route, route_quote = _extract_route(combined)
    if route_quote:
        result.evidence.append(Evidence(field="route", quote=route_quote, source="규칙"))

    result.consciousness, consciousness_quote = _extract_consciousness(combined)
    if consciousness_quote:
        result.evidence.append(
            Evidence(field="consciousness", quote=consciousness_quote, source="규칙")
        )

    rr, spo2, vital_evidence = _extract_vitals(vital_text or combined)
    result.respiratory_rate = rr
    result.spo2 = spo2
    result.evidence.extend(vital_evidence)

    result.alcohol_use = _state_from_patterns(
        combined,
        positive=r"술(?:을|도)?\s*(?:마셨|먹었)|음주\s*(?:함|있음)|소주|맥주|막걸리",
        negative=r"음주\s*(?:없음|안\s*함|하지\s*않)|술은\s*안|술을\s*마시지",
        uncertain=r"(?:술|음주).{0,12}(?:모르|확인\s*필요|미상)|(?:모르|확인\s*필요).{0,12}(?:술|음주)",
    )
    result.multiple_drug_use = _state_from_patterns(
        combined,
        positive=r"여러\s*약.{0,8}(?:먹|복용)|복합복용|다른\s*약.{0,8}(?:같이\s*)?(?:먹|복용)",
        negative=r"단일\s*복용|다른\s*약\s*(?:없|안\s*먹)",
        uncertain=r"다른\s*약.{0,40}(?:확인\s*필요|모르|미상)|복합복용.{0,30}(?:확인\s*필요|모르|미상)",
    )

    if re.search(r"자살|죽고\s*싶|극단적|남은\s*약을\s*전부", combined):
        result.suicide_risk = "확인 필요"
    elif re.search(r"자살시도\s*아님|실수로|오인복용", combined):
        result.suicide_risk = "아니오"
    else:
        result.suicide_risk = "확인 필요"

    result.medicine_container_secured = _state_from_patterns(
        combined,
        positive=r"약통.*(?:발견|확보)|처방전.*(?:발견|확보)|빈\s*약통",
        negative=r"약통\s*(?:없음|못\s*찾)|처방전\s*없",
    )

    known = []
    if result.drug_group:
        known.append(f"{result.drug_group} 의심")
    if result.exposure_time_text:
        known.append(result.exposure_time_text)
    if result.consciousness != "미상":
        known.append(f"의식 {result.consciousness}")
    result.summary = ", ".join(known) if known else "입력에서 구조화 가능한 약물정보가 충분하지 않습니다."
    result.extraction_notes.append("규칙 기반 1차 추출 결과")
    return result


def validate_case(result: DrugExtraction) -> ValidationResult:
    validation = ValidationResult()

    required = {
        "의심 약물 또는 약물군": result.suspected_drug or result.drug_group,
        "복용·노출 시각": result.exposure_time_text,
        "최대 추정량": result.amount_text,
        "노출 경로": None if result.route == "미상" else result.route,
        "의식상태": None if result.consciousness == "미상" else result.consciousness,
        "호흡수": result.respiratory_rate,
        "산소포화도": result.spo2,
        "음주 여부": None if result.alcohol_use in {"미상", "확인 필요"} else result.alcohol_use,
        "복합복용 여부": None if result.multiple_drug_use in {"미상", "확인 필요"} else result.multiple_drug_use,
        "자살시도 가능성": None if result.suicide_risk in {"미상", "확인 필요"} else result.suicide_risk,
    }
    validation.missing_required = [name for name, value in required.items() if value is None]

    # 아래 조건은 UI 시연용 안전 경보다. 실제 배포 전 승인된 소방·의료 지침으로 교체한다.
    if result.consciousness in {"V", "P", "U"}:
        validation.risk_alerts.append("의식 저하 또는 비정상 반응이 기록됨")
    if result.respiratory_rate is not None and (
        result.respiratory_rate < 10 or result.respiratory_rate > 30
    ):
        validation.risk_alerts.append("호흡수 재평가 필요")
    if result.spo2 is not None and result.spo2 < 94:
        validation.risk_alerts.append("산소포화도 저하: 현장 측정값 재확인 필요")
    if result.suicide_risk == "확인 필요":
        validation.risk_alerts.append("자살시도 가능성 추가 확인 필요")

    return validation


def merge_results(rule_result: DrugExtraction, llm_result: DrugExtraction) -> DrugExtraction:
    """숫자·활력징후는 규칙/현장값을 우선하고, 의미 필드는 LLM으로 보완."""
    merged = llm_result.model_copy(deep=True)

    for field in (
        "age_group", "sex", "suspected_drug", "drug_group",
        "exposure_time_text", "exposure_minutes", "amount_text",
        "route", "consciousness", "respiratory_rate", "spo2",
        "medicine_container_secured",
    ):
        rule_value = getattr(rule_result, field)
        if rule_value not in (None, "", "미상"):
            setattr(merged, field, rule_value)

    if rule_result.amount_text:
        merged.amount_exact = rule_result.amount_exact

    # 명시적으로 검출된 상태만 규칙 결과 우선.
    for field in ("alcohol_use", "multiple_drug_use"):
        value = getattr(rule_result, field)
        if value != "미상":
            setattr(merged, field, value)

    merged.evidence = rule_result.evidence + [
        item for item in llm_result.evidence if item not in rule_result.evidence
    ]
    merged.extraction_notes = list(dict.fromkeys(
        rule_result.extraction_notes + llm_result.extraction_notes
    ))
    return merged
