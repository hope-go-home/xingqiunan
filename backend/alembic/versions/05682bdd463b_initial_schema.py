"""initial schema — 所有表结构（从 init_db 迁移到 Alembic 管理）

Revision ID: 05682bdd463b
Revises:
Create Date: 2026-08-21

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "05682bdd463b"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── users ───
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(256), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ─── chat_history ───
    op.create_table(
        "chat_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("session_id", sa.String(32), nullable=False, index=True),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ─── files ───
    op.create_table(
        "files",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("filename", sa.String(256), nullable=False),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("file_size", sa.BigInteger(), server_default="0"),
        sa.Column("status", sa.String(32), server_default="uploaded"),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ─── tasks ───
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("status", sa.String(32), server_default="pending"),
        sa.Column("task_type", sa.String(64), server_default=""),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ─── token_usage ───
    op.create_table(
        "token_usage",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("session_id", sa.String(32), server_default=""),
        sa.Column("mode", sa.String(16), server_default="chat"),
        sa.Column("model", sa.String(64), server_default=""),
        sa.Column("input_tokens", sa.Integer(), server_default="0"),
        sa.Column("output_tokens", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("token_usage")
    op.drop_table("tasks")
    op.drop_table("files")
    op.drop_table("chat_history")
    op.drop_table("users")
