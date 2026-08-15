-- CuVoy durable tables. Apply in the Supabase SQL editor (PROJECT_SPEC §7.12).
-- Service role on Render bypasses RLS; the frontend never uses the service key.

create extension if not exists pgcrypto;

create table if not exists public.users (
  id uuid primary key references auth.users (id) on delete cascade,
  email text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.planning_jobs (
  id uuid primary key,
  user_id uuid references auth.users (id) on delete set null,
  identity_hash text,
  status text not null default 'queued',
  stage text,
  progress integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.trips (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  plan_id text,
  slug uuid not null unique default gen_random_uuid(),
  title text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.exports (
  id uuid primary key default gen_random_uuid(),
  trip_id uuid not null references public.trips (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  kind text not null,
  storage_path text,
  created_at timestamptz not null default now()
);

create index if not exists planning_jobs_user_id_idx on public.planning_jobs (user_id);
create index if not exists trips_user_id_idx on public.trips (user_id);
create index if not exists trips_slug_idx on public.trips (slug);
create index if not exists exports_user_id_idx on public.exports (user_id);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists users_set_updated_at on public.users;
create trigger users_set_updated_at
  before update on public.users
  for each row execute procedure public.set_updated_at();

drop trigger if exists planning_jobs_set_updated_at on public.planning_jobs;
create trigger planning_jobs_set_updated_at
  before update on public.planning_jobs
  for each row execute procedure public.set_updated_at();

drop trigger if exists trips_set_updated_at on public.trips;
create trigger trips_set_updated_at
  before update on public.trips
  for each row execute procedure public.set_updated_at();

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.users (id, email)
  values (new.id, new.email)
  on conflict (id) do update set email = excluded.email;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
