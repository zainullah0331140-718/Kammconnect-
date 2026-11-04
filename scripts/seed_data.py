"""Seed service categories and optional clearly-labelled fictional demo data.

Usage (from the project root, with the virtual environment activated):

    python scripts/seed_data.py
    python scripts/seed_data.py --demo

Demo providers are created with verification status "pending", have "[DEMO]"
in their names, and their descriptions state that they are fictional. They
must never be presented as real or verified businesses.
"""

import argparse
import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from app.core.security import hash_password, validate_password_strength  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.category import ServiceCategory  # noqa: E402
from app.models.enums import ReviewStatus, UserRole, VerificationStatus  # noqa: E402
from app.models.provider import ProviderProfile, ProviderService  # noqa: E402
from app.models.user import User  # noqa: E402
from app.repositories.categories import CategoryRepository  # noqa: E402
from app.repositories.providers import ProviderRepository  # noqa: E402
from app.repositories.reviews import ReviewRepository  # noqa: E402
from app.repositories.users import UserRepository  # noqa: E402

CATEGORIES = [
    ("Electrician", "electrician", "Electrical installation, wiring, and repairs.", "lightning-charge"),
    ("Plumber", "plumber", "Plumbing installation, leaks, and drainage work.", "droplet"),
    ("Mobile Repair", "mobile-repair", "Smartphone screen, battery, and board repairs.", "phone"),
    ("Computer Repair", "computer-repair", "Laptop and desktop repair and maintenance.", "laptop"),
    ("AC Repair", "ac-repair", "Air-conditioner installation, servicing, and repair.", "snow"),
    ("Carpenter", "carpenter", "Furniture, doors, cabinets, and woodwork.", "hammer"),
    ("Painter", "painter", "Interior and exterior painting and finishing.", "brush"),
    ("Other Services", "other-services", "Other skilled local services.", "tools"),
]

DEMO_CUSTOMERS = [
    {"email": "demo.customer1@example.com", "name": "Demo Customer One"},
    {"email": "demo.customer2@example.com", "name": "Demo Customer Two"},
    {"email": "demo.customer3@example.com", "name": "Demo Customer Three"},
]

DEMO_REVIEWS = [
    (
        0,
        5,
        ReviewStatus.APPROVED.value,
        "[DEMO] Fictional review for testing. Clear communication and the work matched the description.",
    ),
    (
        1,
        4,
        ReviewStatus.APPROVED.value,
        "[DEMO] Fictional review for testing. Arrived on time and finished the job as agreed.",
    ),
    (
        2,
        3,
        ReviewStatus.PENDING.value,
        "[DEMO] Fictional review for testing. Waiting for moderation to demonstrate the admin review queue.",
    ),
]

DEMO_PROVIDERS = [
    {
        "email": "demo.electrician@example.com",
        "name": "Demo Electrician",
        "business": "[DEMO] Fictional Electrician Services",
        "city": "Karachi",
        "area": "Gulshan-e-Iqbal",
        "category": "electrician",
        "title": "Demo electrical repair visits",
        "description": "Fictional development profile. This is not a real business and is not verified.",
        "experience": 4,
    },
    {
        "email": "demo.plumber@example.com",
        "name": "Demo Plumber",
        "business": "[DEMO] Fictional Plumbing Works",
        "city": "Lahore",
        "area": "DHA",
        "category": "plumber",
        "title": "Demo plumbing and leak repair",
        "description": "Fictional development profile. This is not a real business and is not verified.",
        "experience": 6,
    },
    {
        "email": "demo.ac@example.com",
        "name": "Demo AC Technician",
        "business": "[DEMO] Fictional AC Care",
        "city": "Islamabad",
        "area": "F-11",
        "category": "ac-repair",
        "title": "Demo AC servicing",
        "description": "Fictional development profile. This is not a real business and is not verified.",
        "experience": 3,
    },
]


def seed_categories(db) -> None:
    repo = CategoryRepository(db)
    created = 0
    for name, slug, description, icon in CATEGORIES:
        existing = repo.get_by_slug(slug)
        if existing is not None:
            continue
        db.add(
            ServiceCategory(
                name=name,
                slug=slug,
                description=description,
                icon=icon,
                is_active=True,
            )
        )
        created += 1
    db.commit()
    print(f"Categories: {created} created, {len(CATEGORIES) - created} already present.")


def seed_demo(db, password: str) -> None:
    users = UserRepository(db)
    providers = ProviderRepository(db)
    categories = CategoryRepository(db)
    for item in DEMO_PROVIDERS:
        if users.get_by_email(item["email"]) is not None:
            print(f"Demo provider already exists: {item['email']}")
            continue
        user = users.create(
            email=item["email"],
            password_hash=hash_password(password),
            full_name=item["name"],
            phone="03000000000",
            role=UserRole.PROVIDER.value,
        )
        profile = providers.create(
            user_id=user.id,
            business_name=item["business"],
            description=item["description"],
            experience_years=item["experience"],
            city=item["city"],
            area=item["area"],
            contact_phone="03000000000",
            whatsapp_number="03000000000",
            verification_status=VerificationStatus.PENDING.value,
        )
        category = categories.get_by_slug(item["category"])
        if category is not None:
            db.add(
                ProviderService(
                    provider_id=profile.id,
                    category_id=category.id,
                    title=item["title"],
                    description=item["description"],
                    price_min=1000,
                    price_max=5000,
                    is_active=True,
                )
            )
        print(f"Created fictional demo provider (pending verification): {item['email']}")
    db.commit()
    print("\nDemo accounts use the password supplied to this script.")
    print("Demo profiles are fictional, labelled [DEMO], and are NOT verified.")


def seed_demo_reviews(db, password: str, max_providers: int = 5) -> None:
    users = UserRepository(db)
    customers = []
    for item in DEMO_CUSTOMERS:
        user = users.get_by_email(item["email"])
        if user is None:
            user = users.create(
                email=item["email"],
                password_hash=hash_password(password),
                full_name=item["name"],
                phone="03000000000",
                role=UserRole.CUSTOMER.value,
            )
            print(f"Created fictional demo customer: {item['email']}")
        customers.append(user)
    db.commit()

    providers = list(
        db.scalars(
            select(ProviderProfile)
            .join(User, User.id == ProviderProfile.user_id)
            .where(
                User.is_active.is_(True),
                User.role == UserRole.PROVIDER.value,
                ProviderProfile.verification_status != VerificationStatus.REJECTED.value,
            )
            .order_by(ProviderProfile.id)
            .limit(max_providers)
        )
    )
    if not providers:
        print("No providers found; run with --demo first to create demo providers.")
        return

    reviews = ReviewRepository(db)
    created = 0
    skipped = 0
    for provider in providers:
        for index, rating, status, comment in DEMO_REVIEWS:
            customer = customers[index]
            if provider.user_id == customer.id or reviews.get_for_customer_provider(
                customer.id, provider.id
            ) is not None:
                skipped += 1
                continue
            reviews.create(
                provider_id=provider.id,
                customer_id=customer.id,
                rating=rating,
                comment=comment,
                status=status,
            )
            created += 1
    db.commit()
    print(f"Demo reviews: {created} created, {skipped} already present or not applicable.")
    print("Demo reviews are clearly labelled [DEMO] and fictional; delete them from admin if not needed.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed KaamConnect reference data")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Also create clearly labelled fictional demo provider accounts",
    )
    parser.add_argument(
        "--demo-reviews",
        action="store_true",
        help="Create clearly labelled fictional demo customers and reviews",
    )
    parser.add_argument(
        "--demo-password",
        help="Password for demo accounts (prefer interactive prompt instead)",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        seed_categories(db)
        if args.demo or args.demo_reviews:
            password = args.demo_password
            if not password:
                password = getpass.getpass("Demo account password: ")
                confirm = getpass.getpass("Confirm demo account password: ")
                if password != confirm:
                    print("Passwords do not match.", file=sys.stderr)
                    return 1
            try:
                validate_password_strength(password)
            except ValueError as exc:
                print(f"Invalid password: {exc}", file=sys.stderr)
                return 1
            if args.demo:
                seed_demo(db, password)
            if args.demo_reviews:
                seed_demo_reviews(db, password)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
