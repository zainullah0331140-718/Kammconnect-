import base64

from fastapi.testclient import TestClient

from app.main import app

PASSWORD = "CustomerPass1"
PROVIDER_PASSWORD = "ProviderPass1"
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def test_public_pages_static_assets_and_security_headers(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "KaamConnect" in response.text
    assert "script-src 'self'" in response.headers["content-security-policy"]

    css = client.get("/static/css/style.css")
    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]

    assert client.get("/privacy").status_code == 200
    assert client.get("/terms").status_code == 200
    assert client.get("/unauthorized").status_code == 403
    assert client.get("/does-not-exist").status_code == 404
    assert client.get("/api/v1/health").json()["database"] == "ok"


def test_customer_registration_csrf_and_login_flow(client, csrf_headers):
    registration = client.post(
        "/api/v1/auth/register/customer",
        json={
            "email": "customer@example.com",
            "password": PASSWORD,
            "full_name": "Test Customer",
            "phone": "03001234567",
        },
    )
    assert registration.status_code == 201
    payload = registration.json()
    assert payload["user"]["role"] == "customer"
    assert client.cookies.get("kc_access")
    assert client.cookies.get("kc_csrf")

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "customer@example.com"

    summary = client.get("/api/v1/users/me/summary")
    assert summary.status_code == 200
    assert summary.json()["favorite_count"] == 0

    blocked = client.post("/api/v1/favorites/1")
    assert blocked.status_code == 403
    assert "CSRF" in blocked.json()["detail"]

    logout = client.post("/api/v1/auth/logout", headers=csrf_headers())
    assert logout.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "customer@example.com", "password": PASSWORD},
    )
    assert login.status_code == 200
    assert login.json()["user"]["full_name"] == "Test Customer"
    assert client.get("/api/v1/auth/me").status_code == 200


def test_admin_sees_all_accounts_and_login_activity(client, make_admin):
    registration = client.post(
        "/api/v1/auth/register/customer",
        json={
            "email": "activity@example.com",
            "password": PASSWORD,
            "full_name": "Activity Customer",
            "phone": "03009990001",
        },
    )
    assert registration.status_code == 201
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "activity@example.com", "password": PASSWORD},
    ).status_code == 200

    make_admin()
    with TestClient(app) as admin_client:
        login = admin_client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "AdminPass1"},
        )
        assert login.status_code == 200

        users = admin_client.get("/api/v1/admin/users?page_size=50")
        assert users.status_code == 200
        items = {item["email"]: item for item in users.json()["items"]}
        assert set(items) >= {"activity@example.com", "admin@example.com"}

        customer = items["activity@example.com"]
        assert customer["login_count"] == 1
        assert customer["last_login_at"]

        admin = items["admin@example.com"]
        assert admin["login_count"] == 1
        assert admin["last_login_at"]

        logins = admin_client.get("/api/v1/admin/audit-logs?action=auth.login")
        assert logins.status_code == 200
        events = logins.json()["items"]
        assert events
        assert all(event["action"] == "auth.login" for event in events)
        assert {event["actor_email"] for event in events} >= {
            "activity@example.com",
            "admin@example.com",
        }


def test_admin_can_upload_profile_photo(client, make_admin):
    make_admin()
    with TestClient(app) as admin_client:
        login = admin_client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "AdminPass1"},
        )
        assert login.status_code == 200

        upload = admin_client.post(
            "/api/v1/users/me/image",
            files={"file": ("admin.png", PNG_BYTES, "image/png")},
            headers={"X-CSRF-Token": admin_client.cookies.get("kc_csrf")},
        )
        assert upload.status_code == 200
        profile_image = upload.json()["profile_image"]
        assert profile_image.startswith("/uploads/profiles/")

        me = admin_client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["profile_image"] == profile_image

        page = admin_client.get("/profile/edit")
        assert page.status_code == 200
        assert 'id="accountImageForm"' in page.text


def test_user_can_delete_own_account(client, csrf_headers):
    registration = client.post(
        "/api/v1/auth/register/customer",
        json={
            "email": "self.delete@example.com",
            "password": PASSWORD,
            "full_name": "Self Delete",
            "phone": "03005556667",
        },
    )
    assert registration.status_code == 201

    missing_password = client.request(
        "DELETE", "/api/v1/users/me", json={}, headers=csrf_headers()
    )
    assert missing_password.status_code == 422

    wrong_password = client.request(
        "DELETE",
        "/api/v1/users/me",
        json={"password": "WrongPass1"},
        headers=csrf_headers(),
    )
    assert wrong_password.status_code == 400
    assert client.get("/api/v1/auth/me").status_code == 200

    deleted = client.request(
        "DELETE",
        "/api/v1/users/me",
        json={"password": PASSWORD},
        headers=csrf_headers(),
    )
    assert deleted.status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "self.delete@example.com", "password": PASSWORD},
    )
    assert login.status_code == 401


def test_provider_can_delete_own_account_and_profile(client, csrf_headers):
    registration = client.post(
        "/api/v1/auth/register/provider",
        json={
            "email": "provider.delete@example.com",
            "password": PROVIDER_PASSWORD,
            "full_name": "Provider Delete",
            "phone": "03007778889",
            "business_name": "Deletable Services",
            "description": "Provider profile created to test self-deletion.",
            "experience_years": 2,
            "city": "Lahore",
            "area": "Gulberg",
            "contact_phone": "03007778889",
            "whatsapp_number": "03007778889",
        },
    )
    assert registration.status_code == 201
    provider_id = client.get("/api/v1/providers/me").json()["id"]

    deleted = client.request(
        "DELETE",
        "/api/v1/users/me",
        json={"password": PROVIDER_PASSWORD},
        headers=csrf_headers(),
    )
    assert deleted.status_code == 204

    search = client.get("/api/v1/providers")
    assert search.status_code == 200
    assert all(item["id"] != provider_id for item in search.json()["items"])


def test_provider_can_upload_profile_and_five_work_photos(client, csrf_headers):
    registration = client.post(
        "/api/v1/auth/register/provider",
        json={
            "email": "work.photos@example.com",
            "password": PROVIDER_PASSWORD,
            "full_name": "Work Photos",
            "phone": "03003334445",
            "business_name": "Photo Finish Services",
            "description": "Provider profile used to test work photo uploads.",
            "experience_years": 3,
            "city": "Lahore",
            "area": "Model Town",
            "contact_phone": "03003334445",
            "whatsapp_number": "03003334445",
        },
    )
    assert registration.status_code == 201
    provider_id = client.get("/api/v1/providers/me").json()["id"]

    profile_image = client.post(
        "/api/v1/providers/me/image",
        files={"file": ("provider.png", PNG_BYTES, "image/png")},
        headers=csrf_headers(),
    )
    assert profile_image.status_code == 200
    assert profile_image.json()["profile_image"].startswith("/uploads/profiles/")

    def photo(index):
        return ("files", (f"work-{index}.png", PNG_BYTES, "image/png"))

    first = client.post(
        "/api/v1/providers/me/work-images",
        files=[photo(1), photo(2)],
        headers=csrf_headers(),
    )
    assert first.status_code == 200
    assert len(first.json()["work_images"]) == 2

    second = client.post(
        "/api/v1/providers/me/work-images",
        files=[photo(index) for index in range(3, 6)],
        headers=csrf_headers(),
    )
    assert second.status_code == 200
    images = second.json()["work_images"]
    assert len(images) == 5
    assert all(image["image_path"].startswith("/uploads/work/") for image in images)

    too_many = client.post(
        "/api/v1/providers/me/work-images",
        files=[photo(6)],
        headers=csrf_headers(),
    )
    assert too_many.status_code == 400
    assert "up to 5" in too_many.json()["detail"]

    public = client.get(f"/api/v1/providers/{provider_id}")
    assert public.status_code == 200
    assert len(public.json()["work_images"]) == 5

    for image in images:
        removed = client.request(
            "DELETE",
            f"/api/v1/providers/me/work-images/{image['id']}",
            headers=csrf_headers(),
        )
        assert removed.status_code == 200
    assert client.get("/api/v1/providers/me").json()["work_images"] == []
    assert client.get(f"/api/v1/providers/{provider_id}").json()["work_images"] == []


def test_provider_search_admin_verification_and_category_flow(client, make_admin):
    registration = client.post(
        "/api/v1/auth/register/provider",
        json={
            "email": "provider@example.com",
            "password": PROVIDER_PASSWORD,
            "full_name": "Test Provider",
            "phone": "03007654321",
            "business_name": "Test Home Services",
            "description": "Test provider for integration coverage.",
            "experience_years": 5,
            "city": "Karachi",
            "area": "Clifton",
            "contact_phone": "03007654321",
            "whatsapp_number": "03007654321",
        },
    )
    assert registration.status_code == 201
    assert registration.json()["user"]["role"] == "provider"

    profile = client.get("/api/v1/providers/me")
    assert profile.status_code == 200
    provider_id = profile.json()["id"]
    assert profile.json()["verification_status"] == "pending"

    public_search = client.get("/api/v1/providers")
    assert public_search.status_code == 200
    assert any(item["id"] == provider_id for item in public_search.json()["items"])
    assert client.get("/api/v1/providers?min_rating=4").status_code == 200
    assert client.get("/api/v1/providers?sort=rating").status_code == 200

    make_admin()
    with TestClient(app) as admin_client:
        login = admin_client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "AdminPass1"},
        )
        assert login.status_code == 200
        admin_headers = {"X-CSRF-Token": admin_client.cookies.get("kc_csrf")}

        stats = admin_client.get("/api/v1/admin/stats")
        assert stats.status_code == 200
        assert stats.json()["total_providers"] == 1
        assert stats.json()["pending_providers"] == 1

        verify = admin_client.patch(
            f"/api/v1/admin/providers/{provider_id}/verification",
            json={"status": "verified", "note": "Checked test documents."},
            headers=admin_headers,
        )
        assert verify.status_code == 200
        assert verify.json()["verification_status"] == "verified"

        create_category = admin_client.post(
            "/api/v1/admin/categories",
            json={"name": "Test Category", "description": "Temporary test category"},
            headers=admin_headers,
        )
        assert create_category.status_code == 201
        category_id = create_category.json()["id"]
        assert create_category.json()["slug"] == "test-category"

        categories = admin_client.get("/api/v1/categories")
        assert categories.status_code == 200
        assert any(item["id"] == category_id for item in categories.json())

        deleted = admin_client.delete(
            f"/api/v1/admin/categories/{category_id}", headers=admin_headers
        )
        assert deleted.status_code == 204

    verified = client.get("/api/v1/providers?verified=true")
    assert verified.status_code == 200
    assert any(item["id"] == provider_id for item in verified.json()["items"])


def test_admin_can_delete_a_provider_account(client, make_admin):
    registration = client.post(
        "/api/v1/auth/register/provider",
        json={
            "email": "delete.me@example.com",
            "password": PROVIDER_PASSWORD,
            "full_name": "Delete Me",
            "phone": "03001112223",
            "business_name": "Disposable Provider",
            "description": "Provider account created only to test deletion.",
            "experience_years": 1,
            "city": "Karachi",
            "area": "Clifton",
            "contact_phone": "03001112223",
            "whatsapp_number": "03001112223",
        },
    )
    assert registration.status_code == 201
    provider_user_id = registration.json()["user"]["id"]
    provider_id = client.get("/api/v1/providers/me").json()["id"]

    admin, password = make_admin()
    with TestClient(app) as admin_client:
        login = admin_client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": password},
        )
        assert login.status_code == 200
        admin_headers = {"X-CSRF-Token": admin_client.cookies.get("kc_csrf")}

        self_delete = admin_client.delete(
            f"/api/v1/admin/users/{admin.id}", headers=admin_headers
        )
        assert self_delete.status_code == 400

        deleted = admin_client.delete(
            f"/api/v1/admin/users/{provider_user_id}", headers=admin_headers
        )
        assert deleted.status_code == 204
        assert admin_client.get("/api/v1/admin/providers").json()["total"] == 0

    search = client.get("/api/v1/providers")
    assert search.status_code == 200
    assert all(item["id"] != provider_id for item in search.json()["items"])
