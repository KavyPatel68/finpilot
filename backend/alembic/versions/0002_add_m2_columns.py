"""add_m2_columns

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-20 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add balance_minor and payment_method to transactions
    op.add_column('transactions', sa.Column('balance_minor', sa.Integer(), nullable=True))
    op.add_column('transactions', sa.Column('payment_method', sa.String(), nullable=True))

    # Recreate document status/filetype enums with new values
    # SQLite doesn't support ALTER COLUMN for enums, but since we store as VARCHAR,
    # the new enum values (needs_mapping, completed, excel) are transparently accepted.
    # No DDL change needed for SQLite — the Enum in SQLAlchemy stores as string.


def downgrade() -> None:
    op.drop_column('transactions', 'balance_minor')
    op.drop_column('transactions', 'payment_method')
