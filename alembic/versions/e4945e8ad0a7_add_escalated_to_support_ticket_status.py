"""add escalated to support ticket status

Revision ID: e4945e8ad0a7
Revises: bf0dd3917422
Create Date: 2026-09-13

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e4945e8ad0a7"

down_revision: Union[str, Sequence[str], None] = "bf0dd3917422"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "ALTER TYPE ticketstatus "
        "ADD VALUE IF NOT EXISTS 'ESCALATED_TO_SUPPORT'"
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass