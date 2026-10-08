"""change embedding dimension to 768

Revision ID: 3f5f7bec609c
Revises: 6e57950fc57b
Create Date: 2026-10-08 07:17:51.812027
"""

from typing import Sequence, Union

from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.

revision: str = "3f5f7bec609c"
down_revision: Union[str, Sequence[str], None] = "6e57950fc57b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
 op.alter_column(
"knowledge_chunks",
"embedding",
existing_type=Vector(384),
type_=Vector(768),
existing_nullable=False,
)

def downgrade() -> None:
 op.alter_column(
"knowledge_chunks",
"embedding",
existing_type=Vector(768),
type_=Vector(384),
existing_nullable=False,
)