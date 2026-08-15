-- Row Level Security: users own their trips (PROJECT_SPEC §7.19).
-- Share links are served by FastAPI with the service role, not by opening every row to anon.

alter table public.users enable row level security;
alter table public.planning_jobs enable row level security;
alter table public.trips enable row level security;
alter table public.exports enable row level security;

revoke all on public.users from anon, authenticated;
revoke all on public.planning_jobs from anon, authenticated;
revoke all on public.trips from anon, authenticated;
revoke all on public.exports from anon, authenticated;

grant select, update on public.users to authenticated;
grant select on public.planning_jobs to authenticated;
grant select, insert, update, delete on public.trips to authenticated;
grant all on public.trips to service_role;
grant select, insert, delete on public.exports to authenticated;

drop policy if exists users_select_own on public.users;
create policy users_select_own
  on public.users for select
  to authenticated
  using (id = auth.uid());

drop policy if exists users_update_own on public.users;
create policy users_update_own
  on public.users for update
  to authenticated
  using (id = auth.uid())
  with check (id = auth.uid());

drop policy if exists planning_jobs_select_own on public.planning_jobs;
create policy planning_jobs_select_own
  on public.planning_jobs for select
  to authenticated
  using (user_id = auth.uid());

drop policy if exists trips_select_own on public.trips;
create policy trips_select_own
  on public.trips for select
  to authenticated
  using (user_id = auth.uid());

drop policy if exists trips_insert_own on public.trips;
create policy trips_insert_own
  on public.trips for insert
  to authenticated
  with check (user_id = auth.uid());

drop policy if exists trips_update_own on public.trips;
create policy trips_update_own
  on public.trips for update
  to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

drop policy if exists trips_delete_own on public.trips;
create policy trips_delete_own
  on public.trips for delete
  to authenticated
  using (user_id = auth.uid());

drop policy if exists trips_manage_own on public.trips;
create policy trips_manage_own
  on public.trips for all
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists exports_select_own on public.exports;
create policy exports_select_own
  on public.exports for select
  to authenticated
  using (user_id = auth.uid());

drop policy if exists exports_insert_own on public.exports;
create policy exports_insert_own
  on public.exports for insert
  to authenticated
  with check (user_id = auth.uid());

drop policy if exists exports_delete_own on public.exports;
create policy exports_delete_own
  on public.exports for delete
  to authenticated
  using (user_id = auth.uid());
