from fastapi import APIRouter

from app.api.v1.routes import (
    admin,
    advertisements,
    auth,
    categories,
    complaints,
    favorites,
    health,
    provider_services,
    providers,
    reviews,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(categories.router)
api_router.include_router(providers.router)
api_router.include_router(provider_services.router)
api_router.include_router(reviews.router)
api_router.include_router(favorites.router)
api_router.include_router(complaints.router)
api_router.include_router(advertisements.router)
api_router.include_router(admin.router)
