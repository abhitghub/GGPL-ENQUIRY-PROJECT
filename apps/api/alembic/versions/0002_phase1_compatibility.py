"""phase 1 compatibility columns and audit tables

Revision ID: 0002_phase1_compatibility
Revises: 0001_supabase_quotes_baseline
Create Date: 2026-05-15
"""
from __future__ import annotations

from alembic import op

revision = "0002_phase1_compatibility"
down_revision = "0001_supabase_quotes_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table quotes add column if not exists org_id uuid")
    op.execute("alter table quotes add column if not exists created_by uuid")
    op.execute("alter table quotes add column if not exists version int not null default 1")
    op.execute("create index if not exists quotes_org_created_idx on quotes (org_id, created_at desc)")
    op.execute(
        """
        create table if not exists extraction_jobs (
            id uuid primary key default gen_random_uuid(),
            org_id uuid,
            created_by uuid,
            quote_id uuid references quotes(id) on delete set null,
            status text not null default 'queued',
            source_type text not null default 'email',
            progress numeric not null default 0,
            message text not null default '',
            items jsonb not null default '[]'::jsonb,
            skipped_count int not null default 0,
            error text,
            created_at timestamptz not null default now(),
            updated_at timestamptz not null default now()
        )
        """
    )
    op.execute("create index if not exists extraction_jobs_org_created_idx on extraction_jobs (org_id, created_at desc)")
    op.execute(
        """
        create table if not exists audit_events (
            id uuid primary key default gen_random_uuid(),
            org_id uuid,
            quote_id uuid references quotes(id) on delete cascade,
            actor_id uuid,
            event_type text not null,
            payload jsonb not null default '{}'::jsonb,
            created_at timestamptz not null default now()
        )
        """
    )
    op.execute("create index if not exists audit_events_quote_created_idx on audit_events (quote_id, created_at desc)")


def downgrade() -> None:
    op.execute("drop table if exists audit_events")
    op.execute("drop table if exists extraction_jobs")
    op.execute("alter table quotes drop column if exists version")
    op.execute("alter table quotes drop column if exists created_by")
    op.execute("alter table quotes drop column if exists org_id")
