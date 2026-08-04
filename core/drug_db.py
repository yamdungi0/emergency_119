from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


def normalize(text: str) -> str:
    return re.sub(r"[^0-9a-zA-Z가-힣]+", "", str(text)).lower()


class DrugDatabase:
    """첨부 CSV는 약물 식별·동의어 보조용으로만 사용합니다.

    치료 지침의 권위 근거로 사용하지 않습니다.
    """

    def __init__(self, csv_path: str | Path | None):
        self.df = pd.DataFrame()
        if csv_path and Path(csv_path).exists():
            self.df = self._read_csv(Path(csv_path))

    @staticmethod
    def _read_csv(path: Path) -> pd.DataFrame:
        last_error: Exception | None = None
        for encoding in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
            try:
                return pd.read_csv(path, encoding=encoding).fillna("")
            except Exception as exc:  # pragma: no cover - encoding fallback
                last_error = exc
        raise RuntimeError(f"CSV를 읽을 수 없습니다: {last_error}")

    def search(self, transcript: str, limit: int = 5) -> list[dict[str, str]]:
        if self.df.empty:
            return []

        normalized = normalize(transcript)
        matches: list[dict[str, str]] = []
        for _, row in self.df.iterrows():
            korean = str(row.get("한글명", "")).strip()
            english = str(row.get("영문명", "")).strip()
            aliases = [normalize(korean), normalize(english)]
            if any(alias and alias in normalized for alias in aliases):
                matches.append(
                    {
                        "한글명": korean,
                        "영문명": english,
                        "분류/구분": str(row.get("분류/구분", "")),
                        "남용정보": str(row.get("남용정보", ""))[:500],
                        "약물정보": str(row.get("약물정보", ""))[:500],
                    }
                )
        return matches[:limit]
