"""Deterministic rule-based resume analyzer.

Produces the exact same ReviewResult schema as the Claude provider, so the
whole app works keylessly. Checks: action-verb usage, quantification rate,
section presence, length, weak-phrase detection, and keyword overlap with a
target job description.
"""

from __future__ import annotations

import re

from ..schemas import BulletRewrite, KeywordMatch, ReviewResult, SectionFeedback
from ..services.rag import tokenize
from .parser import ParsedResume

STRONG_VERBS = frozenset(
    """led built designed developed launched shipped implemented architected
    optimized reduced increased improved migrated automated scaled delivered
    created established drove spearheaded engineered refactored streamlined
    accelerated modernized deployed integrated mentored owned initiated
    analyzed researched published presented negotiated managed coordinated
    consolidated eliminated overhauled revamped transformed""".split()
)

WEAK_PHRASES = [
    "responsible for", "worked on", "helped with", "assisted with", "in charge of",
    "duties included", "participated in", "was involved in", "familiar with",
    "team player", "hard-working", "results-driven", "detail-oriented", "go-getter",
    "synergy", "think outside the box",
]

_NUMBER_RE = re.compile(r"(\d+[%+kKmM]?|\$\d|\d+x)")

EXPECTED_SECTIONS = ["experience", "education", "skills"]
NICE_TO_HAVE_SECTIONS = ["summary", "projects"]

_REWRITE_TEMPLATES = {
    "responsible for": "Owned",
    "worked on": "Built",
    "helped with": "Contributed to",
    "assisted with": "Supported",
    "in charge of": "Led",
    "duties included": "Delivered",
    "participated in": "Collaborated on",
    "was involved in": "Drove",
}


def _bullet_starts_with_strong_verb(bullet: str) -> bool:
    words = tokenize(bullet)
    return bool(words) and words[0] in STRONG_VERBS


def _bullet_is_quantified(bullet: str) -> bool:
    return bool(_NUMBER_RE.search(bullet))


def _find_weak_phrases(text: str) -> list[str]:
    lowered = text.lower()
    return [p for p in WEAK_PHRASES if p in lowered]


def _suggest_rewrite(bullet: str) -> BulletRewrite | None:
    lowered = bullet.lower()
    for weak, strong in _REWRITE_TEMPLATES.items():
        if weak in lowered:
            idx = lowered.index(weak)
            remainder = bullet[idx + len(weak):].strip(" ,.")
            improved = f"{strong} {remainder}" if remainder else strong
            if not _bullet_is_quantified(bullet):
                improved += " — quantify the impact (e.g. '…reducing latency by 30%')"
            return BulletRewrite(
                original=bullet,
                improved=improved,
                rationale=(
                    f"Replaces the passive phrase '{weak}' with the action verb "
                    f"'{strong}' and pushes toward measurable impact."
                ),
            )
    if not _bullet_starts_with_strong_verb(bullet) and len(bullet.split()) >= 4:
        return BulletRewrite(
            original=bullet,
            improved=f"Delivered {bullet[0].lower() + bullet[1:]}".rstrip(".")
            + (" — add a metric to show scale" if not _bullet_is_quantified(bullet) else ""),
            rationale="Bullets should lead with a strong action verb and include measurable results.",
        )
    return None


def extract_jd_keywords(job_description: str, limit: int = 25) -> list[str]:
    """Pick the most salient JD terms (frequency-weighted, dedup'd)."""
    from collections import Counter

    counts = Counter(tokenize(job_description))
    generic = {"experience", "team", "work", "role", "years", "strong", "skills",
               "ability", "including", "using", "knowledge", "plus", "must", "we",
               "requirements", "responsibilities", "preferred", "qualifications"}
    ranked = [t for t, _ in counts.most_common() if t not in generic]
    return ranked[:limit]


def keyword_match(resume_text: str, job_description: str | None) -> KeywordMatch:
    if not job_description or not job_description.strip():
        return KeywordMatch(matched=[], missing=[], match_ratio=0.0)
    jd_terms = extract_jd_keywords(job_description)
    resume_terms = set(tokenize(resume_text))
    matched = [t for t in jd_terms if t in resume_terms]
    missing = [t for t in jd_terms if t not in resume_terms]
    ratio = len(matched) / len(jd_terms) if jd_terms else 0.0
    return KeywordMatch(matched=matched, missing=missing, match_ratio=round(ratio, 3))


def analyze(parsed: ParsedResume, job_description: str | None = None) -> ReviewResult:
    sections: list[SectionFeedback] = []
    strengths: list[str] = []
    ats_notes: list[str] = []

    bullets = parsed.all_bullets
    n_bullets = len(bullets)
    strong_starts = sum(_bullet_starts_with_strong_verb(b) for b in bullets)
    quantified = sum(_bullet_is_quantified(b) for b in bullets)
    verb_rate = strong_starts / n_bullets if n_bullets else 0.0
    quant_rate = quantified / n_bullets if n_bullets else 0.0
    weak = _find_weak_phrases(parsed.raw_text)

    # ---- structure / section presence
    present = set(parsed.section_names)
    missing_required = [s for s in EXPECTED_SECTIONS if s not in present]
    structure_score = 100.0 - 25.0 * len(missing_required)
    structure_score -= 5.0 * len([s for s in NICE_TO_HAVE_SECTIONS if s not in present])
    structure_score = max(0.0, structure_score)
    structure_notes = []
    if missing_required:
        structure_notes.append(
            "Add the missing core section(s): " + ", ".join(missing_required) + "."
        )
    else:
        strengths.append("All core sections (experience, education, skills) are present.")
    if "summary" not in present:
        structure_notes.append("A 2–3 line professional summary helps recruiters orient quickly.")
    sections.append(SectionFeedback(
        section="Structure",
        severity="good" if structure_score >= 85 else "warning" if structure_score >= 60 else "critical",
        score=round(structure_score, 1),
        feedback=(
            "Resume structure looks solid." if not structure_notes
            else "The resume is missing structure recruiters and ATS parsers expect."
        ),
        suggestions=structure_notes,
    ))

    # ---- impact / bullets
    impact_score = 30.0 + 40.0 * verb_rate + 30.0 * quant_rate if n_bullets else 20.0
    impact_suggestions = []
    if n_bullets == 0:
        impact_suggestions.append("Use bullet points (starting with '-' or '•') to describe your work.")
    if verb_rate < 0.6:
        impact_suggestions.append(
            f"Only {strong_starts}/{n_bullets or 0} bullets start with a strong action verb — "
            "lead every bullet with verbs like 'Built', 'Led', 'Optimized'."
        )
    else:
        strengths.append("Most bullets lead with strong action verbs.")
    if quant_rate < 0.4:
        impact_suggestions.append(
            f"Only {quantified}/{n_bullets or 0} bullets contain numbers — quantify impact "
            "with metrics (%, $, time saved, users served)."
        )
    else:
        strengths.append("Good use of quantified, measurable results.")
    sections.append(SectionFeedback(
        section="Impact & Bullet Quality",
        severity="good" if impact_score >= 75 else "warning" if impact_score >= 50 else "critical",
        score=round(min(impact_score, 100.0), 1),
        feedback=(
            f"{strong_starts}/{n_bullets} bullets start with action verbs; "
            f"{quantified}/{n_bullets} are quantified."
            if n_bullets else "No bullet points were detected."
        ),
        suggestions=impact_suggestions,
    ))

    # ---- language
    lang_score = max(0.0, 100.0 - 12.0 * len(weak))
    lang_suggestions = [
        f"Replace the weak phrase '{p}' with a concrete action verb." for p in weak[:5]
    ]
    if not weak:
        strengths.append("No filler phrases or clichés detected.")
    sections.append(SectionFeedback(
        section="Language",
        severity="good" if lang_score >= 85 else "warning" if lang_score >= 60 else "critical",
        score=round(lang_score, 1),
        feedback=(
            "Language is direct and active." if not weak
            else f"Found {len(weak)} weak/cliché phrase(s) that dilute impact."
        ),
        suggestions=lang_suggestions,
    ))

    # ---- length & ATS
    wc = parsed.word_count
    if wc < 200:
        length_score, length_msg = 50.0, "The resume is very short — likely under one page of substance."
    elif wc > 1100:
        length_score, length_msg = 65.0, "The resume is long — tighten to one page (two max for 10+ years)."
    else:
        length_score, length_msg = 95.0, "Length is in a healthy range."
        strengths.append("Resume length is appropriate.")
    if parsed.email is None:
        ats_notes.append("No email address detected — contact info must be machine-readable text.")
    if parsed.phone is None:
        ats_notes.append("No phone number detected in the resume text.")
    ats_notes.append("Use standard section headings and a single-column layout for ATS parsing.")
    sections.append(SectionFeedback(
        section="Length & Format",
        severity="good" if length_score >= 85 else "warning",
        score=round(length_score, 1),
        feedback=f"{length_msg} ({wc} words detected.)",
        suggestions=[] if length_score >= 85 else [length_msg],
    ))

    # ---- keyword match vs JD
    keywords = keyword_match(parsed.raw_text, job_description)
    if job_description and job_description.strip():
        kw_score = 100.0 * keywords.match_ratio
        kw_suggestions = []
        if keywords.missing:
            kw_suggestions.append(
                "Work these JD terms into your resume where truthful: "
                + ", ".join(keywords.missing[:10]) + "."
            )
        sections.append(SectionFeedback(
            section="Job Description Match",
            severity="good" if kw_score >= 60 else "warning" if kw_score >= 35 else "critical",
            score=round(kw_score, 1),
            feedback=(
                f"Resume matches {len(keywords.matched)}/"
                f"{len(keywords.matched) + len(keywords.missing)} key terms from the target role."
            ),
            suggestions=kw_suggestions,
        ))

    # ---- bullet rewrites
    rewrites: list[BulletRewrite] = []
    for bullet in bullets:
        if len(rewrites) >= 5:
            break
        rewrite = _suggest_rewrite(bullet)
        if rewrite:
            rewrites.append(rewrite)

    overall = sum(s.score for s in sections) / len(sections)
    summary_bits = []
    summary_bits.append(
        "Strong foundation" if overall >= 75 else
        "Decent starting point" if overall >= 55 else "Needs significant work"
    )
    worst = min(sections, key=lambda s: s.score)
    summary_bits.append(f"the biggest opportunity is in '{worst.section}' (scored {worst.score:.0f})")
    summary = f"{summary_bits[0]} — {summary_bits[1]}. " + (
        f"Reviewed against the target job description with a "
        f"{keywords.match_ratio:.0%} keyword match." if job_description else
        "No target job description was provided; add one for keyword-match analysis."
    )

    return ReviewResult(
        overall_score=round(overall, 1),
        summary=summary,
        strengths=strengths[:6],
        sections=sections,
        bullet_rewrites=rewrites,
        keywords=keywords,
        ats_notes=ats_notes,
    )
