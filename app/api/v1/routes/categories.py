from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.categories import CategoryRepository
from app.schemas.category import CategoryOut

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)) -> list[CategoryOut]:
    repo = CategoryRepository(db)
    counts = repo.provider_counts()
    return [
        CategoryOut(
            id=category.id,
            name=category.name,
            slug=category.slug,
            description=category.description,
            icon=category.icon,
            is_active=category.is_active,
            provider_count=counts.get(category.id, 0),
        )
        for category in repo.list_active()
    ]


@router.get("/{category_id}", response_model=CategoryOut)
def get_category(category_id: int, db: Session = Depends(get_db)) -> CategoryOut:
    repo = CategoryRepository(db)
    category = repo.get(category_id)
    if category is None or not category.is_active:
        raise HTTPException(status_code=404, detail="Category not found")
    counts = repo.provider_counts()
    return CategoryOut(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        icon=category.icon,
        is_active=category.is_active,
        provider_count=counts.get(category.id, 0),
    )
