-- Idempotent trip RLS for projects that already applied 001/002.
-- Users can insert, select, update, and delete their own saved trips.

grant select, insert, update, delete on public.trips to authenticated;
grant all on public.trips to service_role;

drop policy if exists trips_select_own on public.trips;
create policy trips_select_own
  on public.trips for select
  to authenticated
  using (auth.uid() = user_id);

drop policy if exists trips_insert_own on public.trips;
create policy trips_insert_own
  on public.trips for insert
  to authenticated
  with check (auth.uid() = user_id);

drop policy if exists trips_update_own on public.trips;
create policy trips_update_own
  on public.trips for update
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists trips_delete_own on public.trips;
create policy trips_delete_own
  on public.trips for delete
  to authenticated
  using (auth.uid() = user_id);

drop policy if exists "Users can manage their own trips" on public.trips;
drop policy if exists trips_manage_own on public.trips;
create policy "Users can manage their own trips"
  on public.trips for all
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
