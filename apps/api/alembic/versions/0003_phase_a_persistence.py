"""phase a persistent repository support

Revision ID: 0003_phase_a_persistence
Revises: 0002_phase1_compatibility
Create Date: 2026-05-15
"""
from __future__ import annotations

from alembic import op

revision = "0003_phase_a_persistence"
down_revision = "0002_phase1_compatibility"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table quotes add column if not exists updated_at timestamptz not null default now()")
    op.execute(
        """
        create table if not exists generated_exports (
            token uuid primary key default gen_random_uuid(),
            org_id uuid,
            quote_id uuid references quotes(id) on delete cascade,
            export_type text not null default '',
            filename text not null,
            content_type text not null,
            content bytea not null,
            created_at timestamptz not null default now()
        )
        """
    )
    op.execute("create index if not exists generated_exports_org_created_idx on generated_exports (org_id, created_at desc)")
    op.execute("create index if not exists generated_exports_quote_idx on generated_exports (quote_id)")
    op.execute(
        """
        create table if not exists doc_sessions (
            id uuid primary key default gen_random_uuid(),
            org_id uuid,
            documents jsonb not null default '{}'::jsonb,
            messages jsonb not null default '[]'::jsonb,
            created_at timestamptz not null default now(),
            updated_at timestamptz not null default now()
        )
        """
    )
    op.execute("create index if not exists doc_sessions_org_created_idx on doc_sessions (org_id, created_at desc)")


def downgrade() -> None:
    op.execute("drop table if exists doc_sessions")
    op.execute("drop table if exists generated_exports")
    op.execute("alter table quotes drop column if exists updated_at")
