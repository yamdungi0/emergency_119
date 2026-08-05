from __future__ import annotations

from models import DrugExtraction, ValidationResult
from openai_service import extract_with_openai, is_enabled
from rules import extract_with_rules, merge_results, validate_case


def analyze_case(
    transcript: str,
    field_note: str,
    vital_text: str,
) -> tuple[DrugExtraction, ValidationResult, str]:
    """하이브리드 분석.

    반환:
      result: 구조화 결과
      validation: 누락/위험 경고
      mode: 사용한 분석 경로
    """
    rule_result = extract_with_rules(transcript, field_note, vital_text)

    if not is_enabled():
        result = rule_result
        mode = "규칙 기반 데모"
    else:
        try:
            llm_result = extract_with_openai(transcript, field_note, vital_text)
            result = merge_results(rule_result, llm_result)
            mode = "규칙 + OpenAI 구조화 추출"
        except Exception as exc:
            result = rule_result
            result.extraction_notes.append(
                f"OpenAI 호출 실패로 규칙 기반 결과 사용: {type(exc).__name__}"
            )
            mode = "규칙 기반 대체"

    validation = validate_case(result)
    return result, validation, mode
