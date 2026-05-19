"""app users and roles

Revision ID: 0004_app_users
Revises: 0003_phase_a_persistence
Create Date: 2026-05-19
"""
from __future__ import annotations

from alembic import op

revision = "0004_app_users"
down_revision = "0003_phase_a_persistence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        create table if not exists app_users (
            org_id uuid not null,
            user_id text not null,
            name text not null default '',
            email text not null default '',
            role text not null default 'sales',
            active boolean not null default true,
            created_at timestamptz not null default now(),
            updated_at timestamptz not null default now(),
            primary key (org_id, user_id)
        )
        """
    )
    op.execute("create index if not exists app_users_org_email_idx on app_users (org_id, email)")


def downgrade() -> None:
    op.execute("drop table if exists app_users")
