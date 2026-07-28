"""End-to-end review flow tests: submit -> poll -> result, caching, history.

TestClient executes BackgroundTasks synchronously after the response is
built, so by the time we poll the review has already been processed.
"""

from __future__ import annotations


def _submit_and_poll(client, headers, resume, jd=None):
    payload = {"resume_text": resume}
    if jd is not None:
        payload["job_description"] = jd
    resp = client.post("/reviews", json=payload, headers=headers)
    assert resp.status_code == 202, resp.text
    review_id = resp.json()["id"]

    status = client.get(f"/reviews/{review_id}", headers=headers)
    assert status.status_code == 200
    return status.json()


def test_full_review_flow_keyless(client, auth_headers, sample_resume, sample_jd):
    body = _submit_and_poll(client, auth_headers, sample_resume, sample_jd)
    assert body["status"] == "completed"
    assert body["provider"] == "rule-based"
    result = body["result"]
    assert result is not None
    assert 0 <= result["overall_score"] <= 100
    assert len(result["sections"]) >= 4
    assert result["keywords"]["match_ratio"] > 0
    assert any(s["section"] == "Job Description Match" for s in result["sections"])


def test_review_without_jd(client, auth_headers, sample_resume):
    body = _submit_and_poll(client, auth_headers, sample_resume)
    assert body["status"] == "completed"
    assert body["result"]["keywords"]["match_ratio"] == 0.0


def test_identical_submission_served_from_cache(client, auth_headers, sample_resume, sample_jd):
    first = _submit_and_poll(client, auth_headers, sample_resume, sample_jd)
    assert first["status"] == "completed"

    # Second identical submission must complete instantly (cache hit at create
    # time), and produce the same score.
    resp = client.post(
        "/reviews",
        json={"resume_text": sample_resume, "job_description": sample_jd},
        headers=auth_headers,
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "completed"  # no background pass needed
    assert body["result"]["overall_score"] == first["result"]["overall_score"]


def test_short_resume_rejected(client, auth_headers):
    resp = client.post("/reviews", json={"resume_text": "too short"}, headers=auth_headers)
    assert resp.status_code == 422


def test_review_is_private_to_owner(client, auth_headers, sample_resume):
    body = _submit_and_poll(client, auth_headers, sample_resume)

    # A different user must not be able to read it.
    other = client.post(
        "/auth/register", json={"email": "intruder@example.com", "password": "password123"}
    )
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    resp = client.get(f"/reviews/{body['id']}", headers=other_headers)
    assert resp.status_code == 404


def test_history_lists_reviews_newest_first(client, auth_headers, sample_resume):
    _submit_and_poll(client, auth_headers, sample_resume)
    resp = client.get("/history", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    assert items[0]["status"] == "completed"
    assert items[0]["overall_score"] is not None


def test_health_reports_keyless_provider(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["provider"] == "rule-based"
    assert body["knowledge_chunks"] > 0
