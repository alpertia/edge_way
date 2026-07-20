-- EdgeWay bulut sema (yeni Supabase projesi) — v0
create table if not exists sites (
  id text primary key,
  name text not null,
  created_at timestamptz default now()
);
create table if not exists devices (
  id text primary key,
  site_id text references sites(id),
  hw_model text,
  version text,
  created_at timestamptz default now()
);
create table if not exists heartbeats (
  id bigint generated always as identity primary key,
  device_id text references devices(id),
  ts timestamptz not null,
  temp_c numeric, load1 numeric, mem_used_pct numeric, disk_used_pct numeric,
  payload jsonb
);
create index if not exists heartbeats_device_ts on heartbeats(device_id, ts desc);
create table if not exists alerts (
  id bigint generated always as identity primary key,
  device_id text references devices(id),
  kind text not null,
  severity text not null,
  message text,
  created_at timestamptz default now(),
  resolved_at timestamptz
);
-- RLS: tum tablolarda acilacak; service_role yazar, tenant kullanicisi site_id filtresiyle okur (v1)
