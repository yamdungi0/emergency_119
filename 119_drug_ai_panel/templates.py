from __future__ import annotations

from models import ConfirmedCase, DrugExtraction, ValidationResult


def _v(value, fallback="확인 중"):
    if value in (None, "", "미상"):
        return fallback
    return value


def make_hospital_message(case: ConfirmedCase, age_group: str = "50대", sex: str = "여성") -> str:
    time_text = _v(case.exposure_time_text)
    drug = _v(case.drug_group or case.suspected_drug, "약물")
    amount = _v(case.amount_text)
    consciousness = _v(case.consciousness)
    rr = f"{case.respiratory_rate}회/분" if case.respiratory_rate is not None else "확인 중"
    spo2 = f"{case.spo2}%" if case.spo2 is not None else "확인 중"

    context = []
    if case.alcohol_use in {"미상", "확인 필요"}:
        context.append("음주 여부 확인 중")
    elif case.alcohol_use == "예":
        context.append("음주 동반")
    if case.suicide_risk == "확인 필요":
        context.append("자살시도 가능성 확인 중")
    elif case.suicide_risk == "예":
        context.append("자살시도 의심")
    if case.medicine_container_secured == "예":
        context.append("약통 확보")

    context_text = ", ".join(context) if context else "추가 상황 확인 중"

    return (
        f"{age_group} {sex}입니다.\n\n"
        f"{time_text} {drug} 약물을 과량 복용한 것으로 의심되며, "
        f"복용량은 {amount}입니다.\n\n"
        f"현재 의식 {consciousness}, 호흡수 {rr}, 산소포화도 {spo2}입니다.\n"
        f"{context_text}입니다.\n\n"
        "중환자 대응 및 수용 가능 여부 확인을 요청드립니다."
    )


def make_response_card(result: DrugExtraction, validation: ValidationResult) -> dict[str, list[str]]:
    immediate = [
        "자극에 대한 반응과 기도 유지 가능 여부 확인",
        "호흡수·산소포화도 현장 측정값 재확인",
        "복용 또는 노출 시각 확인",
        "제품명과 최대 추정량 확인",
        "음주·복합복용 여부 확인",
        "약통·처방전 확보 여부 확인",
    ]

    cautions = [
        "확인되지 않은 값을 AI가 임의로 채우지 않음",
        "약물 확인만을 위해 이송을 지연하지 않음",
        "의식·호흡·순환 평가를 우선함",
        "AI 출력은 참고정보이며 최종 판단은 구급대원과 의료지도 담당자가 수행",
    ]

    medical_direction = list(validation.risk_alerts)
    if not medical_direction:
        medical_direction.append("현재 추출값만으로 자동 의료지도 조건을 확정하지 않음")

    return {
        "즉시 확인": immediate,
        "주의 및 금지": cautions,
        "의료지도 검토": medical_direction,
    }
