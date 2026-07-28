"""Shared test fixtures: isolated SQLite DB + FastAPI test client."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Point the app at a throwaway SQLite DB before anything imports app.config
_TEST_DB = BACKEND_DIR / "test_resume_reviewer.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TEST_DB.as_posix()}")
os.environ.pop("ANTHROPIC_API_KEY", None)  # tests always run keyless
os.environ.pop("REDIS_URL", None)

SAMPLE_RESUME = """\
Jane Doe
jane.doe@example.com | (555) 123-4567 | github.com/janedoe

Summary
Software engineer with 3 years of experience building web applications and data pipelines.

Experience
Software Engineer, Acme Corp (2022 - Present)
- Responsible for maintaining the customer dashboard used by internal teams
- Built a REST API with FastAPI serving 2M requests/day, reducing p95 latency by 45%
- Worked on the migration of batch jobs to Airflow
- Led a team of 3 engineers to ship the billing service rewrite, cutting invoice errors 80%

Education
B.S. Computer Science, State University (2018 - 2022)

Skills
Python, TypeScript, FastAPI, React, PostgreSQL, Redis, Docker, GCP
"""

SAMPLE_JD = """\
We are hiring a Backend Software Engineer (Python).
Requirements: 2+ years with Python, FastAPI or Django, strong PostgreSQL and SQL,
Redis caching, Docker, CI/CD with pytest, and cloud experience (GCP or AWS).
Nice to have: Kubernetes, Kafka, LLM integration experience.
"""


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

    # best-effort cleanup of the throwaway DB
    from app.database import engine

    engine.dispose()
    try:
        _TEST_DB.unlink(missing_ok=True)
    except PermissionError:
        pass


@pytest.fixture()
def auth_headers(client):
    import uuid

    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post("/auth/register", json={"email": email, "password": "s3cretpass!"})
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def sample_resume() -> str:
    return SAMPLE_RESUME


@pytest.fixture()
def sample_jd() -> str:
    return SAMPLE_JD
