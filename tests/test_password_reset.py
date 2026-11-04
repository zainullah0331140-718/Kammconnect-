from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models.password_reset_token import PasswordResetToken

PASSWORD = "CustomerPass1"
NEW_PASSWORD = "CustomerPass2"
PROVIDER_PASSWORD = "ProviderPass1"
NEW_PROVIDER_PASSWORD = "ProviderPass2"
ADMIN_PASSWORD = "AdminPass1"
NEW_ADMIN_PASSWORD = "AdminPass2"


def register_customer(client, email="reset.customer@example.com"):
    response = client.post(
        "/api/v1/auth/register/customer",
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": "Reset Customer",
            "phone": "03001230001",
        },
    )
    assert response.status_code == 201
    return response.json()


def request_reset(client, email):
    response = client.post(
        "/api/v1/auth/password-reset/request", json={"email": email}
    )
    assert response.status_code == 200
    return response.json()


def confirm_reset(client, token, new_password):
    return client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": new_password},
    )


def login(client, email, password):
    return client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )


def test_customer_reset_is_single_use_and_revokes_sessions(client):
    registration = register_customer(client, email="reset.customer@example.com")
    old_refresh = registration["refresh_token"]

    payload = request_reset(client, "reset.customer@example.com")
    token = payload["reset_token"]
    assert token
    assert payload["reset_url"].endswith(token)

    confirmed = confirm_reset(client, token, NEW_PASSWORD)
    assert confirmed.status_code == 200
    assert "reset" in confirmed.json()["message"].lower()

    assert login(client, "reset.customer@example.com", PASSWORD).status_code == 401
    assert login(client, "reset.customer@example.com", NEW_PASSWORD).status_code == 200

    reused = confirm_reset(client, token, "AnotherPass3")
    assert reused.status_code == 400

    with TestClient(app) as anonymous_client:
        refresh = anonymous_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
        )
    assert refresh.status_code == 401


def test_reset_does_not_reveal_unknown_accounts(client):
    response = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "nobody@example.com"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["reset_token"] is None
    assert payload["reset_url"] is None
    assert "if an account exists" in payload["message"].lower()


def test_reset_works_for_provider_and_admin_accounts(client, make_admin):
    provider = client.post(
        "/api/v1/auth/register/provider",
        json={
            "email": "reset.provider@example.com",
            "password": PROVIDER_PASSWORD,
            "full_name": "Reset Provider",
            "phone": "03001230002",
            "business_name": "Reset Provider Services",
            "description": "Provider account used to test password reset.",
            "experience_years": 2,
            "city": "Lahore",
            "area": "Gulberg",
            "contact_phone": "03001230002",
            "whatsapp_number": "03001230002",
        },
    )
    assert provider.status_code == 201

    provider_token = request_reset(client, "reset.provider@example.com")["reset_token"]
    assert confirm_reset(client, provider_token, NEW_PROVIDER_PASSWORD).status_code == 200
    assert login(client, "reset.provider@example.com", NEW_PROVIDER_PASSWORD).status_code == 200

    make_admin(email="reset.admin@example.com", password=ADMIN_PASSWORD)
    admin_token = request_reset(client, "reset.admin@example.com")["reset_token"]
    assert confirm_reset(client, admin_token, NEW_ADMIN_PASSWORD).status_code == 200
    assert login(client, "reset.admin@example.com", NEW_ADMIN_PASSWORD).status_code == 200


def test_admin_can_send_reset_link_for_user(client, make_admin):
    registration = register_customer(client, email="admin.reset.target@example.com")
    target_id = registration["user"]["id"]

    make_admin()
    with TestClient(app) as admin_client:
        assert login(admin_client, "admin@example.com", ADMIN_PASSWORD).status_code == 200
        headers = {"X-CSRF-Token": admin_client.cookies.get("kc_csrf")}
        response = admin_client.post(
            f"/api/v1/admin/users/{target_id}/password-reset", headers=headers
        )
        assert response.status_code == 200
        payload = response.json()
        token = payload["reset_token"]
        assert token
        assert payload["reset_url"]
        assert payload["email_sent"] is False

    assert confirm_reset(client, token, NEW_PASSWORD).status_code == 200
    assert login(client, "admin.reset.target@example.com", NEW_PASSWORD).status_code == 200


def test_logged_in_user_can_change_password(client, csrf_headers):
    register_customer(client, email="change.password@example.com")

    wrong = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "WrongPass1", "new_password": NEW_PASSWORD},
        headers=csrf_headers(),
    )
    assert wrong.status_code == 400

    changed = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        headers=csrf_headers(),
    )
    assert changed.status_code == 200
    assert changed.json()["user"]["email"] == "change.password@example.com"

    assert login(client, "change.password@example.com", PASSWORD).status_code == 401
    assert login(client, "change.password@example.com", NEW_PASSWORD).status_code == 200


def test_expired_reset_token_is_rejected(client, session):
    register_customer(client, email="expired.reset@example.com")
    token = request_reset(client, "expired.reset@example.com")["reset_token"]

    record = session.scalar(select(PasswordResetToken))
    assert record is not None
    record.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        minutes=1
    )
    session.commit()

    assert confirm_reset(client, token, NEW_PASSWORD).status_code == 400


def test_password_reset_pages_and_links_render(client):
    forgot = client.get("/forgot-password")
    assert forgot.status_code == 200
    assert "forgotPasswordForm" in forgot.text

    reset = client.get("/reset-password")
    assert reset.status_code == 200
    assert "resetPasswordForm" in reset.text

    login_page = client.get("/login")
    assert login_page.status_code == 200
    assert "/forgot-password" in login_page.text
