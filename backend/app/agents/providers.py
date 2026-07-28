"""Review providers behind a common interface.

- ClaudeProvider: calls the Anthropic API (model: claude-sonnet-5) with an
  engineered prompt (system prompt + few-shot + strict JSON output) grounded
  in retrieved knowledge-base guidance.
- RuleBasedProvider: deterministic analyzer that emits the same schema, so
  the app runs end-to-end without an API key.

Selection happens in `get_provider()`: if ANTHROPIC_API_KEY is set the Claude
provider is used, otherwise the rule-based one. The README documents both
modes honestly.
"""

from __future__ import annotations

import json
import re
from typing import Protocol

from ..config import get_settings
from ..schemas import ReviewResult
from .analyzer import analyze
from .parser import ParsedResume

SYSTEM_PROMPT = """\
You are an expert resume reviewer for software engineering and data roles.
You have reviewed thousands of resumes for FAANG and startup hiring pipelines.

You will receive:
1. A parsed resume (sections and bullets).
2. Retrieved guidance from a curated knowledge base of resume best practices.
3. Optionally, a target job description.

Ground every recommendation in the retrieved guidance when relevant. Be
specific and honest: quote the candidate's actual bullets when suggesting
rewrites, and never invent experience the candidate does not have.

You MUST respond with a single JSON object and nothing else — no markdown
fences, no commentary. The JSON must match this schema exactly:

{
  "overall_score": <float 0-100>,
  "summary": "<2-3 sentence overall assessment>",
  "strengths": ["<string>", ...],
  "sections": [
    {"section": "<name>", "severity": "good"|"warning"|"critical",
     "score": <float 0-100>, "feedback": "<string>", "suggestions": ["<string>", ...]}
  ],
  "bullet_rewrites": [
    {"original": "<verbatim bullet from the resume>",
     "improved": "<rewritten bullet>", "rationale": "<why this is better>"}
  ],
  "keywords": {"matched": ["<term>"...], "missing": ["<term>"...], "match_ratio": <float 0-1>},
  "ats_notes": ["<string>", ...]
}

Scoring calibration: 85+ exceptional, 70-84 strong, 55-69 average with clear
gaps, below 55 needs a rework. Include at least 3 sections and, when the
resume has bullets, at least 2 bullet_rewrites.
"""

FEW_SHOT_EXAMPLE = """\
Example of the expected quality bar for a bullet rewrite:
{"original": "Responsible for maintaining the company website",
 "improved": "Maintained and modernized the company's customer-facing site (Next.js), cutting page load time 40% and lifting conversion 12%",
 "rationale": "Replaces passive 'responsible for' with concrete ownership, names the stack, and quantifies two outcomes."}
"""


class ReviewProvider(Protocol):
    name: str

    def review(
        self,
        parsed: ParsedResume,
        guidance: list[str],
        job_description: str | None,
    ) -> ReviewResult: ...


class RuleBasedProvider:
    """Deterministic keyless provider — same output schema as Claude."""

    name = "rule-based"

    def review(
        self,
        parsed: ParsedResume,
        guidance: list[str],
        job_description: str | None,
    ) -> ReviewResult:
        # Guidance is retrieved for parity/traceability; the deterministic
        # rules already encode the same best practices.
        return analyze(parsed, job_description)


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    # Fall back to the outermost braces
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        return text[start : end + 1]
    return text


class ClaudeProvider:
    """Anthropic-backed provider using prompt engineering + JSON output."""

    name = "claude"

    def __init__(self, api_key: str, model: str) -> None:
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def _build_user_prompt(
        self,
        parsed: ParsedResume,
        guidance: list[str],
        job_description: str | None,
    ) -> str:
        section_dump = "\n\n".join(
            f"## {s.heading}\n{s.text}" for s in parsed.sections
        )
        guidance_dump = "\n\n".join(
            f"[Guidance {i + 1}]\n{g}" for i, g in enumerate(guidance)
        ) or "(no guidance retrieved)"
        jd_block = (
            f"<job_description>\n{job_description}\n</job_description>"
            if job_description
            else "<job_description>None provided — set keywords.match_ratio to 0 and leave matched/missing empty.</job_description>"
        )
        return (
            f"{FEW_SHOT_EXAMPLE}\n\n"
            f"<retrieved_guidance>\n{guidance_dump}\n</retrieved_guidance>\n\n"
            f"<resume sections={parsed.section_names} words={parsed.word_count}>\n"
            f"{section_dump}\n</resume>\n\n"
            f"{jd_block}\n\n"
            "Review the resume now. Respond with the JSON object only."
        )

    def review(
        self,
        parsed: ParsedResume,
        guidance: list[str],
        job_description: str | None,
    ) -> ReviewResult:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": self._build_user_prompt(parsed, guidance, job_description),
                }
            ],
        )
        text = next(
            (block.text for block in response.content if block.type == "text"), ""
        )
        payload = json.loads(_strip_json_fences(text))
        return ReviewResult.model_validate(payload)


def get_provider() -> ReviewProvider:
    settings = get_settings()
    if settings.anthropic_api_key:
        return ClaudeProvider(settings.anthropic_api_key, settings.anthropic_model)
    return RuleBasedProvider()
