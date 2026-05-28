"""Add app user profile fields.

Revision ID: 0005_app_user_profile_fields
Revises: 0004_app_users
Create Date: 2026-05-28
"""
from __future__ import annotations

from alembic import op

revision = "0005_app_user_profile_fields"
down_revision = "0004_app_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table app_users add column if not exists designation text not null default ''")
    op.execute("alter table app_users add column if not exists contact text not null default ''")


def downgrade() -> None:
    op.execute("alter table app_users drop column if exists contact")
    op.execute("alter table app_users drop column if exists designation")
