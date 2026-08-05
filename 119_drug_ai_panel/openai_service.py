from __future__ import annotations

import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from models import DrugExtraction

load_dotenv()


SYSTEM_PROMPT = """
당신은 119 약물사고 상담기록에서 사실을 구조화하는 정보추출기다.

안전 규칙:
1. 입력 문장에 명시되거나 합리적으로 직접 대응되는 정보만 추출한다.
2. 확인되지 않은 제품명, 성분, 복용량, 활력징후를 만들어내지 않는다.
3. 약물군만 확인되면 suspected_drug에는 통화에서 언급된 일반명만 기록하고,
   정확한 제품명을 임의로 추정하지 않는다.
4. '한 통', '전부'처럼 용기 또는 상대 표현이면 amount_exact=false로 둔다.
5. 자살시도 의도가 명시되지 않으면 확정하지 말고 '확인 필요' 또는 '미상'으로 둔다.
6. 처치방법, 해독제, 약물 용량을 제안하지 않는다.
7. 각 주요 추출값에는 가능한 경우 짧은 원문 근거를 evidence에 넣는다.
8. 결과는 지정된 스키마를 엄격히 따른다.
"""


def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")
    return OpenAI(api_key=api_key)


def is_enabled() -> bool:
    use_openai = os.getenv("USE_OPENAI", "true").lower() in {"1", "true", "yes", "y"}
    return use_openai and bool(os.getenv("OPENAI_API_KEY", "").strip())


def extract_with_openai(
    transcript: str,
    field_note: str,
    vital_text: str,
) -> DrugExtraction:
    client = get_client()
    model = os.getenv("OPENAI_MODEL", "gpt-5-mini")

    user_input = f"""
[119 통화 STT]
{transcript or '(없음)'}

[구급대원 현장 평가소견]
{field_note or '(없음)'}

[현장 측정 활력징후]
{vital_text or '(없음)'}

위 내용에서 약물사고 핵심정보만 구조화하라.
"""

    response = client.responses.parse(
        model=model,
        input=[
            {"role": "developer", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
        text_format=DrugExtraction,
    )

    parsed = response.output_parsed
    if parsed is None:
        raise RuntimeError("구조화 결과가 반환되지 않았습니다.")
    parsed.extraction_notes.append(f"OpenAI 구조화 추출 사용: {model}")
    return parsed


def transcribe_audio(uploaded_file) -> str:
    """Streamlit UploadedFile을 OpenAI 음성인식 API에 전달."""
    client = get_client()
    model = os.getenv("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe")

    suffix = Path(uploaded_file.name).suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(uploaded_file.getbuffer())
        temp_path = tmp.name

    try:
        with open(temp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model=model,
                file=audio_file,
                language="ko",
                prompt=(
                    "119 신고 통화입니다. 약물명, 복용량, 복용시각, "
                    "의식상태, 호흡수, 산소포화도 관련 표현을 정확히 전사하세요."
                ),
            )
        return transcript.text
    finally:
        Path(temp_path).unlink(missing_ok=True)
