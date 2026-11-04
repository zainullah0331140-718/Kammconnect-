import logging
from contextlib import asynccontextmanager
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.api.v1.routes import health
from app.core.config import BASE_DIR, settings
from app.core.security import constant_time_compare
from app.core.templates import templates
from app.pages import router as pages_router

logger = logging.getLogger("kaamconnect")

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
CSRF_EXEMPT_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/register/customer",
    "/api/v1/auth/register/provider",
    "/api/v1/auth/password-reset/request",
    "/api/v1/auth/password-reset/confirm",
    "/api/v1/auth/csrf",
}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.ads_upload_path.mkdir(parents=True, exist_ok=True)
    settings.profiles_upload_path.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title=settings.app_name,
    description=(
        "KaamConnect is a local services marketplace API. Customers can find, "
        "favorite, and review verified local service providers. Providers manage "
        "their business profiles, services, and advertisements. Administrators "
        "moderate verification, reviews, complaints, categories, and advertising."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

settings.ads_upload_path.mkdir(parents=True, exist_ok=True)
settings.profiles_upload_path.mkdir(parents=True, exist_ok=True)

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "app" / "static")),
    name="static",
)
app.mount("/uploads", StaticFiles(directory=str(settings.upload_path)), name="uploads")


@app.middleware("http")
async def csrf_protection(request: Request, call_next):
    if (
        request.method not in SAFE_METHODS
        and request.url.path.startswith("/api/")
        and request.url.path not in CSRF_EXEMPT_PATHS
    ):
        has_session_cookie = bool(
            request.cookies.get(settings.access_cookie_name)
            or request.cookies.get(settings.refresh_cookie_name)
        )
        uses_bearer = bool(request.headers.get("authorization"))
        if has_session_cookie and not uses_bearer:
            cookie_token = request.cookies.get(settings.csrf_cookie_name)
            header_token = request.headers.get("x-csrf-token")
            if (
                not cookie_token
                or not header_token
                or not constant_time_compare(cookie_token, header_token)
            ):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed. Refresh the page and try again."},
                )
    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy", "camera=(), microphone=(), geolocation=(self)"
    )
    if request.url.path.startswith(("/docs", "/redoc")):
        csp = (
            "default-src 'self'; img-src 'self' data: https://fastapi.tiangolo.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "font-src 'self' data: https://cdn.jsdelivr.net; "
            "worker-src 'self' blob:; connect-src 'self' https://cdn.jsdelivr.net; "
            "frame-ancestors 'none'; base-uri 'self'"
        )
    else:
        csp = (
            "default-src 'self'; img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; script-src 'self'; "
            "font-src 'self'; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
    response.headers.setdefault("Content-Security-Policy", csp)
    if settings.is_production and settings.cookie_secure:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
    expose_headers=["Retry-After"],
)


def _wants_json(request: Request) -> bool:
    return request.url.path.startswith("/api/") or request.url.path in {
        "/openapi.json",
        "/health",
    }


def _page_error(request: Request, template: str, status_code: int, message: str):
    return templates.TemplateResponse(
        request=request,
        name=template,
        context={
            "title": "Something went wrong"
            if status_code >= 500
            else "Page not available",
            "page": "error",
            "status_code": status_code,
            "message": message,
        },
        status_code=status_code,
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if _wants_json(request):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None),
        )
    if exc.status_code == 403:
        return _page_error(
            request,
            "403.html",
            403,
            "You do not have permission to open this page.",
        )
    if exc.status_code == 404:
        return _page_error(
            request, "404.html", 404, "The page or record you requested was not found."
        )
    if exc.status_code == 401:
        return RedirectResponse(
            url=f"/login?next={quote(request.url.path)}", status_code=303
        )
    if exc.status_code >= 500:
        return _page_error(
            request, "500.html", 500, "An unexpected server error occurred."
        )
    return _page_error(request, "404.html", exc.status_code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", []) if part != "body")
        errors.append(
            {
                "field": location or "request",
                "message": error.get("msg", "Invalid value"),
                "type": error.get("type", "validation_error"),
            }
        )
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation failed", "errors": errors},
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.warning("Database integrity error: %s", exc.__class__.__name__)
    if _wants_json(request):
        return JSONResponse(
            status_code=409,
            content={"detail": "This record conflicts with existing data."},
        )
    return _page_error(
        request, "500.html", 409, "This action conflicts with existing data."
    )


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request: Request, exc: SQLAlchemyError):
    logger.exception("Database error")
    if _wants_json(request):
        return JSONResponse(
            status_code=500,
            content={"detail": "A server error occurred. Please try again later."},
        )
    return _page_error(
        request, "500.html", 500, "A database error occurred. Please try again later."
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled application error")
    if _wants_json(request):
        return JSONResponse(
            status_code=500,
            content={"detail": "A server error occurred. Please try again later."},
        )
    return _page_error(
        request, "500.html", 500, "An unexpected server error occurred."
    )


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return RedirectResponse(url="/static/images/favicon.svg", status_code=307)


app.include_router(health.router)
app.include_router(api_router, prefix="/api/v1")
app.include_router(pages_router)

