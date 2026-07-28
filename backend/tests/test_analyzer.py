"""Rule-based analyzer tests — the keyless provider must emit a valid schema."""

from app.agents.analyzer import analyze, keyword_match
from app.agents.parser import parse_resume
from app.schemas import ReviewResult


def test_analyzer_produces_valid_schema(sample_resume, sample_jd):
    result = analyze(parse_resume(sample_resume), sample_jd)
    # Round-trips through strict validation
    ReviewResult.model_validate(result.model_dump())
    assert 0 <= result.overall_score <= 100
    assert len(result.sections) >= 4


def test_detects_weak_phrases(sample_resume):
    result = analyze(parse_resume(sample_resume))
    lang = next(s for s in result.sections if s.section == "Language")
    assert lang.score < 100  # "Responsible for" / "Worked on" are present
    assert any("responsible for" in s.lower() for s in lang.suggestions)


def test_bullet_rewrites_target_weak_bullets(sample_resume):
    result = analyze(parse_resume(sample_resume))
    assert result.bullet_rewrites
    originals = " ".join(r.original.lower() for r in result.bullet_rewrites)
    assert "responsible for" in originals or "worked on" in originals


def test_keyword_match_against_jd(sample_resume, sample_jd):
    km = keyword_match(sample_resume, sample_jd)
    assert "python" in km.matched
    assert "fastapi" in km.matched
    assert "kubernetes" in km.missing
    assert 0 < km.match_ratio < 1


def test_no_jd_yields_empty_keywords(sample_resume):
    km = keyword_match(sample_resume, None)
    assert km.matched == [] and km.missing == [] and km.match_ratio == 0.0


def test_missing_sections_lower_structure_score():
    sparse = parse_resume("John Smith\njohn@example.com\nSome text about myself.")
    result = analyze(sparse)
    structure = next(s for s in result.sections if s.section == "Structure")
    assert structure.score <= 40
    assert structure.severity in ("warning", "critical")
