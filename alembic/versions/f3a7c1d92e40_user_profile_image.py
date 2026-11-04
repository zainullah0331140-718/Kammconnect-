"""user profile image

Revision ID: f3a7c1d92e40
Revises: d4e8a1c72b90
Create Date: 2026-11-03 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3a7c1d92e40'
down_revision: Union[str, None] = 'd4e8a1c72b90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('profile_image', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'profile_image')
