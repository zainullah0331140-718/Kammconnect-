"""provider work images

Revision ID: b7c31d9f4a20
Revises: fa12a6fda67c
Create Date: 2026-10-31 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7c31d9f4a20'
down_revision: Union[str, None] = 'fa12a6fda67c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'provider_work_images',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
        sa.Column('provider_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('image_path', sa.String(length=255), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('position >= 0', name=op.f('ck_provider_work_images_position_non_negative')),
        sa.ForeignKeyConstraint(['provider_id'], ['provider_profiles.id'], name=op.f('fk_provider_work_images_provider_id_provider_profiles'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_provider_work_images'))
    )
    op.create_index(op.f('ix_provider_work_images_provider_id'), 'provider_work_images', ['provider_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_provider_work_images_provider_id'), table_name='provider_work_images')
    op.drop_table('provider_work_images')
