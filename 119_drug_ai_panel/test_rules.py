from rules import extract_with_rules, validate_case
from sample_data import SAMPLE_FIELD_NOTE, SAMPLE_TRANSCRIPT, SAMPLE_VITALS


def main():
    result = extract_with_rules(SAMPLE_TRANSCRIPT, SAMPLE_FIELD_NOTE, SAMPLE_VITALS)
    assert result.drug_group == "수면제·진정제"
    assert result.exposure_minutes == 40
    assert result.route == "경구"
    assert result.amount_text == "1통 추정·정확량 미상"
    assert result.alcohol_use == "확인 필요"
    assert result.multiple_drug_use == "확인 필요"
    assert result.consciousness == "V"
    assert result.respiratory_rate == 9
    assert result.spo2 == 90
    assert result.medicine_container_secured == "예"

    validation = validate_case(result)
    assert "음주 여부" in validation.missing_required
    assert "복합복용 여부" in validation.missing_required
    assert "자살시도 가능성" in validation.missing_required
    assert "호흡수 재평가 필요" in validation.risk_alerts
    assert any("산소포화도" in item for item in validation.risk_alerts)
    print("규칙 기반 스모크 테스트 통과")
    print(result.model_dump_json(indent=2))
    print(validation.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
