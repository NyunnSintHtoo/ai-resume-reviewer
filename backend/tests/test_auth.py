"""Auth flow tests: register, duplicate email, login, bad password, /me."""


def test_register_and_me(client):
    resp = client.post(
        "/auth/register", json={"email": "alice@example.com", "password": "password123"}
    )
    assert resp.status_code == 201
    token = resp.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"


def test_register_duplicate_email(client):
    payload = {"email": "bob@example.com", "password": "password123"}
    assert client.post("/auth/register", json=payload).status_code == 201
    assert client.post("/auth/register", json=payload).status_code == 409


def test_login_success_and_failure(client):
    client.post("/auth/register", json={"email": "carol@example.com", "password": "password123"})

    ok = client.post("/auth/login", json={"email": "carol@example.com", "password": "password123"})
    assert ok.status_code == 200
    assert ok.json()["access_token"]

    bad = client.post("/auth/login", json={"email": "carol@example.com", "password": "wrongpass1"})
    assert bad.status_code == 401


def test_protected_route_requires_token(client):
    assert client.get("/history").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer notatoken"}).status_code == 401


def test_password_hashing_roundtrip():
    from app.auth import hash_password, verify_password

    hashed = hash_password("hunter2hunter2")
    assert hashed != "hunter2hunter2"
    assert verify_password("hunter2hunter2", hashed)
    assert not verify_password("wrong-password", hashed)
    assert not verify_password("hunter2hunter2", "malformed-hash")
