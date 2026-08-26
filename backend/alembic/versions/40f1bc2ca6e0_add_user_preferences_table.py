"""add user_preferences table

Revision ID: 40f1bc2ca6e0
Revises: 05682bdd463b
Create Date: 2026-08-26 12:24:17.939948

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '40f1bc2ca6e0'
down_revision: Union[str, Sequence[str], None] = '05682bdd463b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建用户偏好表（跨会话长期记忆）"""
    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("key", sa.String(50), nullable=False),
        sa.Column("value", sa.Text(), server_default=""),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("user_preferences")
