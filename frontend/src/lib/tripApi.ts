import {
  AccountDeleteResponseSchema,
  PATH_ACCOUNT,
  PATH_TRIPS,
  PATH_TRIPS_GET,
  PATH_TRIPS_SHARED,
  SavedTripSchema,
  SharedTripSchema,
  TripListSchema,
  type AccountDeleteResponse,
  type PlanResult,
  type SavedTrip,
  type SaveTripRequest,
  type SharedTrip,
  type TripList,
} from "@cuvoy/contracts";

import { fetchBackend } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import { PlanApiError } from "@/lib/planApi";
import { getSupabaseBrowserClient } from "@/lib/supabase";

async function authedHeaders(extra?: HeadersInit, accessToken?: string | null): Promise<Headers> {
  const headers = new Headers(extra);
  const token = accessToken || (await getAccessToken());
  if (!token) {
    throw new PlanApiError("Login is required to save or list trips.", 401, null);
  }
  headers.set("Authorization", `Bearer ${token}`);
  return headers;
}

async function throwIfNotOk(response: Response): Promise<void> {
  if (response.ok) {
    return;
  }
  let message = `Request failed (${response.status})`;
  try {
    const body = (await response.json()) as { message?: string; detail?: { message?: string } };
    message = body.message || body.detail?.message || message;
  } catch {
    /* keep default */
  }
  throw new PlanApiError(message, response.status, null);
}

function shareUrl(slug: string): string {
  const origin = typeof window !== "undefined" ? window.location.origin : "";
  return `${origin}/trip/${slug}`;
}

async function saveTripViaBrowser(
  body: SaveTripRequest,
  result: PlanResult | null,
): Promise<SavedTrip | null> {
  const supabase = getSupabaseBrowserClient();
  if (!supabase || !result) {
    return null;
  }
  const { data: sessionData } = await supabase.auth.getUser();
  const userId = body.user_id || sessionData.user?.id;
  if (!userId) {
    return null;
  }
  const title =
    body.title?.trim() ||
    (result.itinerary.days[0]?.city ? `Trip to ${result.itinerary.days[0].city}` : "Saved trip");
  const row = {
    id: crypto.randomUUID(),
    user_id: userId,
    plan_id: body.plan_id,
    slug: crypto.randomUUID(),
    title,
    payload: result,
  };
  const { data, error } = await supabase
    .from("trips")
    .insert(row)
    .select("id, slug, title, plan_id")
    .single();
  if (error || !data) {
    return null;
  }
  return SavedTripSchema.parse({
    trip_id: data.id,
    slug: data.slug,
    title: data.title,
    plan_id: data.plan_id,
    share_url: shareUrl(String(data.slug)),
  });
}

async function listTripsViaBrowser(): Promise<TripList | null> {
  const supabase = getSupabaseBrowserClient();
  if (!supabase) {
    return null;
  }
  const { data, error } = await supabase
    .from("trips")
    .select("id, slug, title, plan_id")
    .order("created_at", { ascending: false });
  if (error || !data) {
    return null;
  }
  return TripListSchema.parse({
    trips: data.map((row) => {
    const tripId = String(row.id || "").trim();
    const slug = String(row.slug || tripId).trim();
      return {
        trip_id: tripId,
        slug,
        title: String(row.title || "Untitled trip"),
        plan_id: row.plan_id ? String(row.plan_id) : null,
        share_url: slug ? shareUrl(slug) : null,
      };
    }),
  });
}

export async function saveTrip(
  body: SaveTripRequest,
  timeoutMs: number,
  result?: PlanResult | null,
  accessToken?: string | null,
): Promise<SavedTrip> {
  if (!body.user_id) {
    throw new PlanApiError("Login is required to save or list trips.", 401, null);
  }
  try {
    const response = await fetchBackend(PATH_TRIPS, {
      method: "POST",
      headers: await authedHeaders({ "Content-Type": "application/json" }, accessToken),
      body: JSON.stringify(body),
      timeoutMs,
    });
    await throwIfNotOk(response);
    return SavedTripSchema.parse(await response.json());
  } catch (error) {
    const fallback = await saveTripViaBrowser(body, result ?? null);
    if (fallback) {
      return fallback;
    }
    throw error;
  }
}

export async function listTrips(timeoutMs: number): Promise<TripList> {
  try {
    const response = await fetchBackend(PATH_TRIPS, {
      method: "GET",
      headers: await authedHeaders(),
      cache: "no-store",
      timeoutMs,
    });
    await throwIfNotOk(response);
    const listed = TripListSchema.parse(await response.json());
    if (listed.trips.length > 0) {
      return listed;
    }
    return (await listTripsViaBrowser()) ?? listed;
  } catch (error) {
    const fallback = await listTripsViaBrowser();
    if (fallback) {
      return fallback;
    }
    throw error;
  }
}

export function tripOpenHref(trip: SavedTrip): string {
  const tripId = trip.trip_id?.trim();
  const planId = trip.plan_id?.trim() || tripId;
  if (!planId) {
    return "/saved";
  }
  return tripId ? `/plan/${encodeURIComponent(planId)}?trip=${encodeURIComponent(tripId)}` : `/plan/${encodeURIComponent(planId)}`;
}

export function tripSharePath(trip: SavedTrip): string {
  const slug = trip.slug?.trim() || trip.trip_id?.trim();
  return slug ? `/trip/${encodeURIComponent(slug)}` : "/saved";
}

export function tripShareAbsolute(trip: SavedTrip): string {
  const origin = typeof window !== "undefined" ? window.location.origin : "";
  return `${origin}${tripSharePath(trip)}`;
}

export async function getOwnedTrip(tripId: string, timeoutMs: number): Promise<SharedTrip> {
  const path = PATH_TRIPS_GET.replace("{id}", encodeURIComponent(tripId));
  const response = await fetchBackend(path, {
    method: "GET",
    headers: await authedHeaders(),
    cache: "no-store",
    timeoutMs,
  });
  await throwIfNotOk(response);
  return SharedTripSchema.parse(await response.json());
}

export async function getSharedTrip(slug: string, timeoutMs: number): Promise<SharedTrip> {
  const path = PATH_TRIPS_SHARED.replace("{slug}", encodeURIComponent(slug));
  const response = await fetchBackend(path, {
    method: "GET",
    cache: "no-store",
    timeoutMs,
  });
  await throwIfNotOk(response);
  return SharedTripSchema.parse(await response.json());
}

export async function deleteAccount(timeoutMs: number): Promise<AccountDeleteResponse> {
  const response = await fetchBackend(PATH_ACCOUNT, {
    method: "DELETE",
    headers: await authedHeaders(),
    timeoutMs,
  });
  await throwIfNotOk(response);
  return AccountDeleteResponseSchema.parse(await response.json());
}
