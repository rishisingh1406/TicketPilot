"""add embeddings to knowledge chunks

Revision ID: 3251ba6a5b22

Revises: 3cfee17bd3ff

Create Date: 2026-09-21 19:20:33.472407
"""

from typing import Sequence, Union

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3251ba6a5b22"
down_revision: Union[str, Sequence[str], None] = "3cfee17bd3ff"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "knowledge_chunks",
        sa.Column(
            "embedding",
            Vector(384),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column(
        "knowledge_chunks",
        "embedding",
    )