"""Step 1 of the agentic pipeline: parse a raw resume into structured sections.

Heuristic parser — recognizes common section headings, groups lines under
them, and extracts bullet points. Deterministic so it is unit-testable and
works identically in keyless mode.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SECTION_ALIASES: dict[str, list[str]] = {
    "summary": ["summary", "professional summary", "objective", "profile", "about", "about me"],
    "experience": [
        "experience", "work experience", "professional experience", "employment",
        "employment history", "work history", "relevant experience", "internships",
    ],
    "education": ["education", "academic background", "academics"],
    "skills": ["skills", "technical skills", "core competencies", "technologies", "tech stack"],
    "projects": ["projects", "personal projects", "selected projects", "portfolio"],
    "certifications": ["certifications", "certificates", "licenses"],
    "awards": ["awards", "honors", "achievements", "accomplishments"],
    "publications": ["publications", "research"],
    "volunteering": ["volunteering", "volunteer experience", "community"],
    "contact": ["contact", "contact information"],
}

_ALIAS_TO_CANON = {
    alias: canon for canon, aliases in SECTION_ALIASES.items() for alias in aliases
}

_BULLET_RE = re.compile(r"^\s*[-•·*▪◦‣o]\s+(.*)$")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")


@dataclass
class ParsedSection:
    name: str  # canonical name, e.g. "experience"
    heading: str  # heading as written in the resume
    lines: list[str] = field(default_factory=list)
    bullets: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


@dataclass
class ParsedResume:
    raw_text: str
    sections: list[ParsedSection] = field(default_factory=list)
    email: str | None = None
    phone: str | None = None
    word_count: int = 0

    def get(self, name: str) -> ParsedSection | None:
        for section in self.sections:
            if section.name == name:
                return section
        return None

    @property
    def all_bullets(self) -> list[str]:
        return [b for s in self.sections for b in s.bullets]

    @property
    def section_names(self) -> list[str]:
        return [s.name for s in self.sections]


def _match_heading(line: str) -> tuple[str, str] | None:
    """Return (canonical, as-written) if the line looks like a section heading."""
    stripped = line.strip().strip(":").strip()
    if not stripped or len(stripped) > 40:
        return None
    normalized = re.sub(r"[^a-z ]", "", stripped.lower()).strip()
    canon = _ALIAS_TO_CANON.get(normalized)
    if canon:
        return canon, stripped
    return None


def parse_resume(text: str) -> ParsedResume:
    parsed = ParsedResume(raw_text=text, word_count=len(text.split()))
    parsed.email = m.group(0) if (m := _EMAIL_RE.search(text)) else None
    parsed.phone = m.group(1).strip() if (m := _PHONE_RE.search(text)) else None

    header = ParsedSection(name="header", heading="Header")
    current = header
    parsed.sections.append(header)

    for line in text.splitlines():
        if not line.strip():
            continue
        matched = _match_heading(line)
        if matched:
            canon, heading = matched
            current = ParsedSection(name=canon, heading=heading)
            parsed.sections.append(current)
            continue
        bullet = _BULLET_RE.match(line)
        if bullet:
            current.bullets.append(bullet.group(1).strip())
        current.lines.append(line.strip())

    # Drop an empty header pseudo-section
    parsed.sections = [s for s in parsed.sections if s.lines or s.name != "header"]
    return parsed
