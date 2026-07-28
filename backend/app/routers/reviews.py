"""Review endpoints.

Submissions are processed asynchronously with FastAPI BackgroundTasks; the
client polls GET /reviews/{id} until status is completed/failed. Identical
(resume, JD, provider) submissions are served from the response cache.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..auth import get_current_identity
from ..cache import get_cache, review_cache_key
from ..config import get_settings
from ..database import SessionLocal, get_db
from ..models import Review, User
from ..schemas import ReviewResult, ReviewStatusResponse, ReviewSubmitRequest
from ..services.pdf import PdfExtractionError, extract_text_from_pdf
from ..agents.pipeline import run_review_pipeline
from ..agents.providers import get_provider

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reviews", tags=["reviews"])

MAX_PDF_BYTES = 5 * 1024 * 1024


def _process_review(review_id: str) -> None:
    """Background worker: runs the agentic pipeline and stores the result."""
    settings = get_settings()
    db = SessionLocal()
    try:
        review = db.get(Review, review_id)
        if review is None:
            return
        review.status = "processing"
        db.commit()

        run = run_review_pipeline(review.resume_text, review.job_description)
        result_json = run.result.model_dump_json()

        review.status = "completed"
        review.provider = run.provider_name
        review.result_json = result_json
        review.overall_score = run.result.overall_score
        review.completed_at = datetime.now(timezone.utc)
        db.commit()

        if review.cache_key:
            get_cache().set(review.cache_key, json.loads(result_json), settings.cache_ttl_seconds)
    except Exception as exc:
        logger.exception("Review %s failed", review_id)
        review = db.get(Review, review_id)
        if review is not None:
            review.status = "failed"
            review.error = str(exc)[:2000]
            review.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


def _create_review(
    db: Session,
    background: BackgroundTasks,
    user: User,
    resume_text: str,
    job_description: str | None,
) -> Review:
    provider_name = get_provider().name
    cache_key = review_cache_key(resume_text, job_description, provider_name)
    cached = get_cache().get(cache_key)

    review = Review(
        user_id=user.id,
        resume_text=resume_text,
        job_description=job_description,
        provider=provider_name,
        cache_key=cache_key,
    )

    if cached is not None:
        # Cache hit: complete instantly without re-running the pipeline.
        result = ReviewResult.model_validate(cached)
        review.status = "completed"
        review.result_json = result.model_dump_json()
        review.overall_score = result.overall_score
        review.completed_at = datetime.now(timezone.utc)
        db.add(review)
        db.commit()
        return review

    db.add(review)
    db.commit()
    background.add_task(_process_review, review.id)
    return review


@router.post("", response_model=ReviewStatusResponse, status_code=status.HTTP_202_ACCEPTED)
def submit_review(
    payload: ReviewSubmitRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_identity),
) -> ReviewStatusResponse:
    review = _create_review(db, background, user, payload.resume_text, payload.job_description)
    return _to_status(review)


@router.post("/upload", response_model=ReviewStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_review_pdf(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    job_description: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_identity),
) -> ReviewStatusResponse:
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=415, detail="Only PDF uploads are supported")
    data = await file.read()
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF exceeds the 5 MB limit")
    try:
        resume_text = extract_text_from_pdf(data)
    except PdfExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if len(resume_text) < 50:
        raise HTTPException(status_code=422, detail="Extracted resume text is too short")
    review = _create_review(db, background, user, resume_text, job_description)
    return _to_status(review)


@router.get("/{review_id}", response_model=ReviewStatusResponse)
def get_review(
    review_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_identity),
) -> ReviewStatusResponse:
    review = db.get(Review, review_id)
    if review is None or review.user_id != user.id:
        raise HTTPException(status_code=404, detail="Review not found")
    return _to_status(review)


def _to_status(review: Review) -> ReviewStatusResponse:
    result = None
    if review.result_json:
        result = ReviewResult.model_validate_json(review.result_json)
    return ReviewStatusResponse(
        id=review.id,
        status=review.status,  # type: ignore[arg-type]
        provider=review.provider,
        created_at=review.created_at,
        completed_at=review.completed_at,
        error=review.error,
        result=result,
    )
