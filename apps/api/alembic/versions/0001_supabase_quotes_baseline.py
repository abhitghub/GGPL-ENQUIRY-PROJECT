"""supabase quotes baseline

Revision ID: 0001_supabase_quotes_baseline
Revises:
Create Date: 2026-05-15
"""
from __future__ import annotations

from alembic import op

revision = "0001_supabase_quotes_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("create extension if not exists pgcrypto")
    op.execute(
        """
        create table if not exists quotes (
            id uuid primary key default gen_random_uuid(),
            created_at timestamptz default now(),
            quote_no text not null default '',
            customer text not null default '',
            project_ref text not null default '',
            custom_label text not null default '',
            timestamp text not null default '',
            n_items int not null default 0,
            n_ready int not null default 0,
            n_check int not null default 0,
            n_missing int not null default 0,
            n_regret int not null default 0,
            items jsonb not null default '[]'::jsonb,
            quote_data jsonb not null default '{}'::jsonb,
            quote_pdf_b64 text not null default '',
            quote_pdf_name text not null default '',
            stage text not null default 'initial',
            stage_history jsonb not null default '[]'::jsonb,
            stage_meta jsonb not null default '{}'::jsonb
        )
        """
    )
    op.execute("create index if not exists quotes_created_at_idx on quotes (created_at desc)")
    op.execute("create index if not exists quotes_customer_idx on quotes (customer)")
    op.execute("create index if not exists quotes_stage_idx on quotes (stage)")
    op.execute("alter table quotes enable row level security")


def downgrade() -> None:
    op.execute("drop table if exists quotes")
