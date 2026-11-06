from fastapi.testclient import TestClient

from app.main import app

PASSWORD = "ComplaintPass1"


def register_customer(client, email):
    response = client.post(
        "/api/v1/auth/register/customer",
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": "Complaint Tester",
            "phone": "03001234000",
        },
    )
    assert response.status_code == 201
    return response.json()["user"]


def filer_complaint(client, csrf_headers):
    response = client.post(
        "/api/v1/complaints",
        json={
            "subject": "Test complaint subject",
            "message": "This complaint exists only to verify delete behaviour.",
        },
        headers=csrf_headers(),
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_complaint_delete_owner_admin_permissions_and_audit(
    client, csrf_headers, make_admin
):
    register_customer(client, "complaint.owner@example.com")
    complaint_id = filer_complaint(client, csrf_headers)

    with TestClient(app) as other_client:
        register_customer(other_client, "complaint.other@example.com")
        other_headers = {"X-CSRF-Token": other_client.cookies.get("kc_csrf")}
        blocked = other_client.request(
            "DELETE",
            f"/api/v1/complaints/{complaint_id}",
            headers=other_headers,
        )
        assert blocked.status_code == 403

    deleted = client.request(
        "DELETE", f"/api/v1/complaints/{complaint_id}", headers=csrf_headers()
    )
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/complaints/{complaint_id}").status_code == 404

    admin_target = filer_complaint(client, csrf_headers)
    make_admin()
    with TestClient(app) as admin_client:
        login = admin_client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "AdminPass1"},
        )
        assert login.status_code == 200
        admin_headers = {"X-CSRF-Token": admin_client.cookies.get("kc_csrf")}

        admin_delete = admin_client.delete(
            f"/api/v1/admin/complaints/{admin_target}", headers=admin_headers
        )
        assert admin_delete.status_code == 204
        assert (
            admin_client.get(f"/api/v1/complaints/{admin_target}").status_code == 404
        )

        logs = admin_client.get("/api/v1/admin/audit-logs?action=complaint.delete")
        assert logs.status_code == 200
        assert any(
            item["entity_id"] == str(admin_target) for item in logs.json()["items"]
        )
