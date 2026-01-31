from pydantic import BaseModel
from typing import Literal


class Correction(BaseModel):
    original: str
    corrected: str
    reason: str


class Claim(BaseModel):
    claim: str
    speaker: str | None = None
    confidence_level: Literal["high", "medium", "low"]
    topic_tags: list[str]
    is_hot_take: bool = False
    hot_take_reason: str | None = None


class CleaningResult(BaseModel):
    cleaned_transcript: str
    corrections: list[Correction]


class ClaimsResult(BaseModel):
    claims: list[Claim]


class AnalysisResult(BaseModel):
    video_id: str
    cleaned_transcript: str
    corrections_made: list[Correction]
    claims: list[Claim]
    summary: str
