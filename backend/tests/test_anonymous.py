"""Anonymous identity tests: the whole review flow works with only an
X-Anon-Id header (no JWT), scoped per browser identity."""

from __future__ import annotations

import uuid


def _anon_headers() -> dict:
    return {"X-Anon-Id": str(uuid.uuid4())}


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


def test_anonymous_full_review_flow(client, sample_resume, sample_jd):
    headers = _anon_headers()
    body = _submit_and_poll(client, headers, sample_resume, sample_jd)
    assert body["status"] == "completed"
    assert body["result"] is not None
    assert 0 <= body["result"]["overall_score"] <= 100


def test_anonymous_history_scoped_to_anon_id(client, sample_resume):
    headers = _anon_headers()
    _submit_and_poll(client, headers, sample_resume)

    mine = client.get("/history", headers=headers)
    assert mine.status_code == 200
    assert len(mine.json()) == 1

    # A different browser (different anon id) sees an empty history.
    other = client.get("/history", headers=_anon_headers())
    assert other.status_code == 200
    assert other.json() == []


def test_anonymous_cannot_read_other_anon_review(client, sample_resume):
    headers = _anon_headers()
    body = _submit_and_poll(client, headers, sample_resume)

    resp = client.get(f"/reviews/{body['id']}", headers=_anon_headers())
    assert resp.status_code == 404


def test_anon_id_is_stable_across_requests(client, sample_resume):
    headers = _anon_headers()
    _submit_and_poll(client, headers, sample_resume)
    _submit_and_poll(client, headers, sample_resume + "\nExtra line of content here.")
    hist = client.get("/history", headers=headers)
    assert len(hist.json()) == 2


def test_invalid_anon_id_rejected(client, sample_resume):
    for bad in ("short", "x" * 65, "has spaces in it", "bad!chars#here"):
        resp = client.post(
            "/reviews",
            json={"resume_text": sample_resume},
            headers={"X-Anon-Id": bad},
        )
        assert resp.status_code == 401, bad


def test_no_identity_at_all_rejected(client, sample_resume):
    resp = client.post("/reviews", json={"resume_text": sample_resume})
    assert resp.status_code == 401


def test_jwt_takes_precedence_over_anon_header(client, auth_headers, sample_resume):
    # A request carrying both identities is scoped to the JWT user.
    anon = str(uuid.uuid4())
    headers = {**auth_headers, "X-Anon-Id": anon}
    body = _submit_and_poll(client, headers, sample_resume)
    assert body["status"] == "completed"

    # The anon identity alone must not see the JWT user's review.
    resp = client.get(f"/reviews/{body['id']}", headers={"X-Anon-Id": anon})
    assert resp.status_code == 404
