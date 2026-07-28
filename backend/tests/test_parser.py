"""Resume parser tests."""

from app.agents.parser import parse_resume


def test_parses_sections(sample_resume):
    parsed = parse_resume(sample_resume)
    names = parsed.section_names
    assert "summary" in names
    assert "experience" in names
    assert "education" in names
    assert "skills" in names


def test_extracts_contact_info(sample_resume):
    parsed = parse_resume(sample_resume)
    assert parsed.email == "jane.doe@example.com"
    assert parsed.phone is not None


def test_extracts_bullets(sample_resume):
    parsed = parse_resume(sample_resume)
    exp = parsed.get("experience")
    assert exp is not None
    assert len(exp.bullets) == 4
    assert any("FastAPI" in b for b in exp.bullets)


def test_unstructured_text_falls_into_header():
    parsed = parse_resume("Just a plain paragraph with no headings at all.")
    assert parsed.section_names == ["header"]
    assert parsed.word_count == 9


def test_heading_detection_is_case_insensitive():
    parsed = parse_resume("WORK EXPERIENCE\n- Did a thing\nEDUCATION:\nSome school")
    assert "experience" in parsed.section_names
    assert "education" in parsed.section_names
