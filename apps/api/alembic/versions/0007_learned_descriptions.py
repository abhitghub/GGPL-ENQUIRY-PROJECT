"""Add the learned-descriptions store (portal description memory).

Revision ID: 0007_learned_descriptions
Revises: 0006_app_user_password_hash
Create Date: 2026-07-31
"""
from __future__ import annotations

from alembic import op

revision = "0007_learned_descriptions"
down_revision = "0006_app_user_password_hash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        create table if not exists learned_descriptions (
            id uuid primary key default gen_random_uuid(),
            org_id uuid,
            fingerprint text not null default '',
            source_text text not null default '',
            ggpl_description text not null default '',
            fields jsonb not null default '{}'::jsonb,
            customer text not null default '',
            status text not null default 'pending',
            source text not null default 'edit',
            note text not null default '',
            created_by text not null default '',
            approved_by text not null default '',
            hit_count integer not null default 0,
            last_applied_at timestamptz,
            created_at timestamptz not null default now(),
            updated_at timestamptz not null default now()
        )
        """
    )
    op.execute(
        "create index if not exists learned_descriptions_org_fingerprint_idx "
        "on learned_descriptions (org_id, fingerprint)"
    )
    op.execute(
        "create index if not exists learned_descriptions_org_updated_idx "
        "on learned_descriptions (org_id, updated_at desc)"
    )


def downgrade() -> None:
    op.execute("drop table if exists learned_descriptions")
