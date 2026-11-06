from fastapi.testclient import TestClient

from app.main import app

PASSWORD = "ActivityPass1"


def test_admin_can_clear_activity_log_and_clear_is_audited(client, make_admin):
    make_admin()
    with TestClient(app) as admin_client:
        login = admin_client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "AdminPass1"},
        )
        assert login.status_code == 200
        headers = {"X-CSRF-Token": admin_client.cookies.get("kc_csrf")}

        before = admin_client.get("/api/v1/admin/audit-logs?page_size=50")
        assert before.status_code == 200
        assert before.json()["total"] >= 1

        cleared = admin_client.delete("/api/v1/admin/audit-logs", headers=headers)
        assert cleared.status_code == 204

        after = admin_client.get("/api/v1/admin/audit-logs?page_size=50")
        assert after.status_code == 200
        assert after.json()["total"] == 1
        entry = after.json()["items"][0]
        assert entry["action"] == "audit.clear"
        assert entry["actor_email"] == "admin@example.com"


def test_clear_activity_log_requires_admin(client, csrf_headers):
    registration = client.post(
        "/api/v1/auth/register/customer",
        json={
            "email": "activity.customer@example.com",
            "password": PASSWORD,
            "full_name": "Activity Customer",
            "phone": "03001119999",
        },
    )
    assert registration.status_code == 201

    response = client.request(
        "DELETE", "/api/v1/admin/audit-logs", headers=csrf_headers()
    )
    assert response.status_code == 403
