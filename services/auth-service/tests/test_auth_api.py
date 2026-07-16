from __future__ import annotations

from app.demo_users import DEMO_PASSWORD, DEMO_USERS


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_seed_users_is_idempotent(client):
    first = await client.post("/auth/dev/seed-users")
    assert first.status_code == 200
    assert len(first.json()["created"]) == len(DEMO_USERS)

    second = await client.post("/auth/dev/seed-users")
    assert second.status_code == 200
    assert second.json()["created"] == []
    assert len(second.json()["already_existed"]) == len(DEMO_USERS)


async def test_full_login_mfa_flow(client):
    await client.post("/auth/dev/seed-users")
    demo = DEMO_USERS[0]

    login_resp = await client.post("/auth/login", json={"email": demo.email, "password": DEMO_PASSWORD})
    assert login_resp.status_code == 200
    bridge_token = login_resp.json()["mfa_bridge_token"]

    otp_resp = await client.get("/auth/dev/mfa-code", params={"email": demo.email})
    assert otp_resp.status_code == 200
    otp_code = otp_resp.json()["otp_code"]

    verify_resp = await client.post(
        "/auth/mfa/verify", json={"mfa_bridge_token": bridge_token, "otp_code": otp_code}
    )
    assert verify_resp.status_code == 200
    body = verify_resp.json()
    assert body["role"] == demo.role
    assert body["sub"] == demo.email

    me_resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me_resp.status_code == 200
    assert me_resp.json() == {"sub": demo.email, "role": demo.role, "mfa_verified": True}


async def test_login_wrong_password_rejected(client):
    await client.post("/auth/dev/seed-users")
    demo = DEMO_USERS[0]
    resp = await client.post("/auth/login", json={"email": demo.email, "password": "wrong-password"})
    assert resp.status_code == 401


async def test_login_unknown_email_rejected(client):
    resp = await client.post("/auth/login", json={"email": "nobody@sc-tpcrs.demo", "password": DEMO_PASSWORD})
    assert resp.status_code == 401


async def test_mfa_verify_wrong_code_rejected(client):
    await client.post("/auth/dev/seed-users")
    demo = DEMO_USERS[0]
    login_resp = await client.post("/auth/login", json={"email": demo.email, "password": DEMO_PASSWORD})
    bridge_token = login_resp.json()["mfa_bridge_token"]

    resp = await client.post(
        "/auth/mfa/verify", json={"mfa_bridge_token": bridge_token, "otp_code": "000000"}
    )
    assert resp.status_code in (401, 400)


async def test_me_requires_bearer_token(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401
