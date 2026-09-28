"""add review required ticket status

Revision ID: 3f50ba346be1
Revises: 46e8219f5d85
Create Date: 2026-09-28

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "3f50ba346be1"
down_revision: Union[str, Sequence[str], None] = "46e8219f5d85"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add REVIEW_REQUIRED to the ticketstatus enum."""

    op.execute(
        "ALTER TYPE ticketstatus ADD VALUE IF NOT EXISTS 'REVIEW_REQUIRED'"
    )


def downgrade() -> None:
    """PostgreSQL enum values cannot safely be removed in place."""

    pass