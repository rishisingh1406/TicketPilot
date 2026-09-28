"""update reviewer action enum

Revision ID: 5858a27753d5
Revises: 3f50ba346be1
Create Date: 2026-09-28 06:20:46.668083

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5858a27753d5"
down_revision: Union[str, Sequence[str], None] = "3f50ba346be1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update reviewer action enum to match the current application model."""

    op.execute(
        """
        ALTER TABLE reviews
        ALTER COLUMN reviewer_action TYPE VARCHAR
        USING reviewer_action::text
        """
    )

    op.execute("DROP TYPE revieweraction")

    op.execute(
        """
        CREATE TYPE revieweraction AS ENUM (
            'RESOLVE',
            'EDIT_AND_RESOLVE',
            'TAKE_OVER'
        )
        """
    )

    op.execute(
        """
        ALTER TABLE reviews
        ALTER COLUMN reviewer_action
        TYPE revieweraction
        USING reviewer_action::revieweraction
        """
    )


def downgrade() -> None:
    """Restore the previous reviewer action enum."""

    op.execute(
        """
        ALTER TABLE reviews
        ALTER COLUMN reviewer_action TYPE VARCHAR
        USING reviewer_action::text
        """
    )

    op.execute("DROP TYPE revieweraction")

    op.execute(
        """
        CREATE TYPE revieweraction AS ENUM (
            'APPROVE',
            'EDIT',
            'ESCALATE'
        )
        """
    )

    op.execute(
        """
        ALTER TABLE reviews
        ALTER COLUMN reviewer_action
        TYPE revieweraction
        USING reviewer_action::revieweraction
        """
    )