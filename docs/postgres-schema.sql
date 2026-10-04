-- Reference schema only. Apply through reviewed migrations in a deployment.
create table finance_event (
  event_id uuid primary key,
  source_system text not null,
  source_record_id text not null,
  occurred_on timestamptz not null,
  amount numeric(18,2) not null,
  payload jsonb not null,
  source_hash text not null,
  unique (source_system, source_record_id)
);

create table review_item (
  review_id uuid primary key,
  event_id uuid not null references finance_event(event_id),
  reason_code text not null,
  confidence numeric(4,3) not null check (confidence between 0 and 1),
  status text not null check (status in ('open', 'approved', 'rejected', 'investigate')),
  decided_by uuid,
  decided_at timestamptz
);

create table audit_event (
  audit_id uuid primary key,
  actor_id text not null,
  action text not null,
  object_type text not null,
  object_id text not null,
  occurred_at timestamptz not null default now(),
  lineage jsonb not null
);

-- Enable row-level security and define organization-specific policies before use.
