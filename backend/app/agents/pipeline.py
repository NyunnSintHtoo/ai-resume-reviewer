"""The agentic review workflow.

A four-step pipeline:

  1. PARSE     — structure the raw resume into sections/bullets (parser.py)
  2. RETRIEVE  — pull relevant guidance from the RAG knowledge base (rag.py)
  3. GENERATE  — produce a structured review via the active provider
                 (Claude with engineered prompts, or the rule-based analyzer)
  4. CRITIQUE  — validate the review JSON against the strict Pydantic schema;
                 on failure, retry generation once with the validation errors
                 fed back, then fall back to the deterministic provider.

Each step records a trace entry so the pipeline is observable and testable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from pydantic import ValidationError

from ..config import get_settings
from ..schemas import ReviewResult
from ..services.rag import get_knowledge_base
from .parser import ParsedResume, parse_resume
from .providers import ReviewProvider, RuleBasedProvider, get_provider

logger = logging.getLogger(__name__)


@dataclass
class PipelineRun:
    result: ReviewResult
    provider_name: str
    trace: list[str] = field(default_factory=list)


def _retrieve_guidance(parsed: ParsedResume, job_description: str | None, top_k: int) -> list[str]:
    kb = get_knowledge_base()
    query_parts = [
        "resume best practices",
        " ".join(parsed.section_names),
        parsed.raw_text[:1500],
    ]
    if job_description:
        query_parts.append(job_description[:1500])
    hits = kb.search(" ".join(query_parts), top_k=top_k)
    return [f"({chunk.title}) {chunk.text}" for chunk, _score in hits]


def _critique(candidate: object) -> tuple[ReviewResult | None, str | None]:
    """Validate a candidate result against the schema. Returns (result, error)."""
    try:
        if isinstance(candidate, ReviewResult):
            # Re-validate: providers may hand back constructed models
            return ReviewResult.model_validate(candidate.model_dump()), None
        return ReviewResult.model_validate(candidate), None
    except ValidationError as exc:
        return None, str(exc)


def run_review_pipeline(
    resume_text: str,
    job_description: str | None = None,
    provider: ReviewProvider | None = None,
) -> PipelineRun:
    settings = get_settings()
    provider = provider or get_provider()
    trace: list[str] = []

    # Step 1 — parse
    parsed = parse_resume(resume_text)
    trace.append(
        f"parse: {len(parsed.sections)} sections, {len(parsed.all_bullets)} bullets, "
        f"{parsed.word_count} words"
    )

    # Step 2 — retrieve
    guidance = _retrieve_guidance(parsed, job_description, settings.rag_top_k)
    trace.append(f"retrieve: {len(guidance)} guidance chunks from knowledge base")

    # Step 3 — generate
    candidate = provider.review(parsed, guidance, job_description)
    trace.append(f"generate: provider={provider.name}")

    # Step 4 — critique (validate; retry once; deterministic fallback)
    result, error = _critique(candidate)
    if result is None:
        trace.append(f"critique: validation failed, retrying once ({error[:200]})")
        logger.warning("Review failed schema validation, retrying: %s", error)
        try:
            candidate = provider.review(parsed, guidance, job_description)
            result, error = _critique(candidate)
        except Exception as exc:  # provider error on retry
            result, error = None, str(exc)
        if result is None:
            trace.append("critique: retry failed, falling back to rule-based provider")
            fallback = RuleBasedProvider()
            result = fallback.review(parsed, guidance, job_description)
            provider = fallback
    trace.append("critique: schema valid")

    return PipelineRun(result=result, provider_name=provider.name, trace=trace)
