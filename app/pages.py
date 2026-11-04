from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.templates import templates

router = APIRouter(tags=["Pages"])


def render(request: Request, template: str, *, title: str, page: str, **context):
    return templates.TemplateResponse(
        request=request,
        name=template,
        context={"title": title, "page": page, **context},
    )


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return render(request, "home.html", title="Find trusted local services", page="home")


@router.get("/search", response_class=HTMLResponse)
def search(request: Request):
    return render(request, "search.html", title="Search service providers", page="search")


@router.get("/providers/{provider_id}", response_class=HTMLResponse)
def provider_detail(request: Request, provider_id: int):
    return render(
        request,
        "provider_detail.html",
        title="Provider details",
        page="provider-detail",
        provider_id=provider_id,
    )


@router.get("/categories", response_class=HTMLResponse)
def categories(request: Request):
    return render(
        request, "categories.html", title="Service categories", page="categories"
    )


@router.get("/register", response_class=HTMLResponse)
def register_customer(request: Request):
    return render(
        request,
        "register_customer.html",
        title="Create a customer account",
        page="register-customer",
    )


@router.get("/register/provider", response_class=HTMLResponse)
def register_provider(request: Request):
    return render(
        request,
        "register_provider.html",
        title="Become a service provider",
        page="register-provider",
    )


@router.get("/login", response_class=HTMLResponse)
def login(request: Request):
    return render(request, "login.html", title="Log in", page="login")


@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password(request: Request):
    return render(
        request,
        "forgot_password.html",
        title="Forgot password",
        page="forgot-password",
    )


@router.get("/reset-password", response_class=HTMLResponse)
def reset_password(request: Request):
    return render(
        request,
        "reset_password.html",
        title="Reset password",
        page="reset-password",
    )


@router.get("/dashboard/customer", response_class=HTMLResponse)
def customer_dashboard(request: Request):
    return render(
        request,
        "dashboard_customer.html",
        title="Customer dashboard",
        page="customer-dashboard",
    )


@router.get("/dashboard/provider", response_class=HTMLResponse)
def provider_dashboard(request: Request):
    return render(
        request,
        "dashboard_provider.html",
        title="Provider dashboard",
        page="provider-dashboard",
    )


@router.get("/profile/edit", response_class=HTMLResponse)
def edit_profile(request: Request):
    return render(
        request, "profile_edit.html", title="Edit profile", page="profile-edit"
    )


@router.get("/provider/services", response_class=HTMLResponse)
def manage_services(request: Request):
    return render(
        request,
        "provider_services.html",
        title="Manage services",
        page="manage-services",
    )


@router.get("/favorites", response_class=HTMLResponse)
def favorites(request: Request):
    return render(request, "favorites.html", title="My favorites", page="favorites")


@router.get("/reviews", response_class=HTMLResponse)
def reviews(request: Request):
    return render(request, "reviews.html", title="Reviews", page="reviews")


@router.get("/complaints", response_class=HTMLResponse)
def complaints(request: Request):
    return render(
        request, "complaints.html", title="Complaints", page="complaints"
    )


@router.get("/advertisements", response_class=HTMLResponse)
def advertisements(request: Request):
    return render(
        request,
        "advertisements.html",
        title="Advertising",
        page="advertisements",
    )


@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    return render(
        request, "admin_dashboard.html", title="Admin dashboard", page="admin-dashboard"
    )


@router.get("/admin/users", response_class=HTMLResponse)
def admin_users(request: Request):
    return render(
        request, "admin_users.html", title="Manage users", page="admin-users"
    )


@router.get("/admin/verification", response_class=HTMLResponse)
def admin_verification(request: Request):
    return render(
        request,
        "admin_verification.html",
        title="Provider verification",
        page="admin-verification",
    )


@router.get("/admin/categories", response_class=HTMLResponse)
def admin_categories(request: Request):
    return render(
        request,
        "admin_categories.html",
        title="Manage categories",
        page="admin-categories",
    )


@router.get("/admin/reviews", response_class=HTMLResponse)
def admin_reviews(request: Request):
    return render(
        request, "admin_reviews.html", title="Moderate reviews", page="admin-reviews"
    )


@router.get("/admin/complaints", response_class=HTMLResponse)
def admin_complaints(request: Request):
    return render(
        request,
        "admin_complaints.html",
        title="Manage complaints",
        page="admin-complaints",
    )


@router.get("/admin/activity", response_class=HTMLResponse)
def admin_activity(request: Request):
    return render(
        request, "admin_activity.html", title="Activity log", page="admin-activity"
    )


@router.get("/admin/advertisements", response_class=HTMLResponse)
def admin_advertisements(request: Request):
    return render(
        request,
        "admin_advertisements.html",
        title="Manage advertisements",
        page="admin-advertisements",
    )


@router.get("/unauthorized", response_class=HTMLResponse)
def unauthorized(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="403.html",
        context={"title": "Unauthorized", "page": "error"},
        status_code=403,
    )


@router.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request):
    return render(request, "privacy.html", title="Privacy policy", page="static")


@router.get("/terms", response_class=HTMLResponse)
def terms(request: Request):
    return render(request, "terms.html", title="Terms of service", page="static")
