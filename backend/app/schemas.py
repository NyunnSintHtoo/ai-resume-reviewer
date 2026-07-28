"""Pydantic schemas — including the strict review-result schema that both
providers (Claude and rule-based) must satisfy. The critic pass in the agent
pipeline validates against ReviewResult and triggers a retry on failure.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

Severity = Literal["good", "warning", "critical"]


# ---------------------------------------------------------------- auth
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str


# ---------------------------------------------------------------- review result
class SectionFeedback(BaseModel):
    section: str = Field(description="Section name, e.g. 'Experience'")
    severity: Severity
    score: float = Field(ge=0, le=100)
    feedback: str = Field(min_length=1)
    suggestions: list[str] = Field(default_factory=list)


class BulletRewrite(BaseModel):
    original: str = Field(min_length=1)
    improved: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class KeywordMatch(BaseModel):
    matched: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    match_ratio: float = Field(ge=0, le=1)


class ReviewResult(BaseModel):
    """The structured review contract. Every provider must emit exactly this."""

    overall_score: float = Field(ge=0, le=100)
    summary: str = Field(min_length=1)
    strengths: list[str] = Field(default_factory=list)
    sections: list[SectionFeedback] = Field(min_length=1)
    bullet_rewrites: list[BulletRewrite] = Field(default_factory=list)
    keywords: KeywordMatch
    ats_notes: list[str] = Field(default_factory=list)

    @field_validator("overall_score")
    @classmethod
    def _round_score(cls, v: float) -> float:
        return round(v, 1)


# ---------------------------------------------------------------- API shapes
class ReviewSubmitRequest(BaseModel):
    resume_text: str = Field(min_length=50, description="Plain-text resume content")
    job_description: str | None = None


class ReviewStatusResponse(BaseModel):
    id: str
    status: Literal["pending", "processing", "completed", "failed"]
    provider: str
    created_at: datetime
    completed_at: datetime | None = None
    error: str | None = None
    result: ReviewResult | None = None


class ReviewListItem(BaseModel):
    id: str
    status: str
    provider: str
    overall_score: float | None
    created_at: datetime
    job_description_preview: str | None = None
