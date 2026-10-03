"""Add deterministic content hash to knowledge chunks.

Revision ID: 6e57950fc57b
Revises: 5858a27753d5
Create Date: 2026-10-03 06:31:02.492331
"""

from typing import Sequence, Union
import hashlib

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6e57950fc57b"
down_revision: Union[str, Sequence[str], None] = "5858a27753d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _build_content_hash(
    content: str,
    source: str,
    timestamp,
) -> str:
    """Build a deterministic identity hash for a knowledge chunk."""
    normalized_content = content.strip()

    identity = (
        normalized_content
        + "|"
        + source
        + "|"
        + (timestamp.isoformat() if timestamp else "")
    )

    return hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()


def upgrade() -> None:
    """Add content hashes, remove duplicate chunks, and enforce uniqueness."""

    # 1. Add the column as nullable because existing rows do not have hashes yet.
    op.add_column(
        "knowledge_chunks",
        sa.Column(
            "content_hash",
            sa.String(),
            nullable=True,
        ),
    )

    connection = op.get_bind()

    # 2. Read existing knowledge chunks.
    rows = connection.execute(
        sa.text(
            """
            SELECT
                chunk_id,
                content,
                source,
                timestamp
            FROM knowledge_chunks
            ORDER BY chunk_id
            """
        )
    ).fetchall()

    # 3. Generate deterministic hashes for existing rows.
    for row in rows:
        content_hash = _build_content_hash(
            content=row.content,
            source=row.source,
            timestamp=row.timestamp,
        )

        connection.execute(
            sa.text(
                """
                UPDATE knowledge_chunks
                SET content_hash = :content_hash
                WHERE chunk_id = :chunk_id
                """
            ),
            {
                "content_hash": content_hash,
                "chunk_id": row.chunk_id,
            },
        )

    # 4. Remove duplicate rows.
    #
    # Keep the lowest chunk_id for each content_hash.
    connection.execute(
        sa.text(
            """
            DELETE FROM knowledge_chunks AS kc
            WHERE kc.chunk_id NOT IN (
                SELECT MIN(chunk_id)
                FROM knowledge_chunks
                GROUP BY content_hash
            )
            """
        )
    )

    # 5. content_hash is now populated for every remaining row.
    op.alter_column(
        "knowledge_chunks",
        "content_hash",
        existing_type=sa.String(),
        nullable=False,
    )

    # 6. Enforce uniqueness at the database level.
    op.create_unique_constraint(
        "uq_knowledge_chunks_content_hash",
        "knowledge_chunks",
        ["content_hash"],
    )


def downgrade() -> None:
    """Remove the content hash constraint and column."""

    op.drop_constraint(
        "uq_knowledge_chunks_content_hash",
        "knowledge_chunks",
        type_="unique",
    )

    op.drop_column(
        "knowledge_chunks",
        "content_hash",
    )