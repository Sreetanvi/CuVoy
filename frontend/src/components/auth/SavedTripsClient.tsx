"use client";

import { WARM_GENERATION_TIMEOUT_MS, type SavedTrip } from "@cuvoy/contracts";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { LoginButtons } from "@/components/auth/LoginButtons";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { listTrips, tripOpenHref, tripShareAbsolute, tripSharePath } from "@/lib/tripApi";

function SavedTripCard({ trip }: { trip: SavedTrip }) {
  const [copied, setCopied] = useState(false);
  const tripId = trip.trip_id?.trim();
  const slug = trip.slug?.trim() || tripId;
  const openHref = tripOpenHref(trip);
  const shareHref = tripSharePath(trip);
  const canOpen = Boolean(trip.plan_id?.trim() || tripId);
  const canShare = Boolean(slug);

  async function copyShare() {
    const url = tripShareAbsolute(trip);
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <li className="rounded-md border border-border px-4 py-3">
      <p className="font-medium">{trip.title}</p>
      <div className="mt-2 flex flex-wrap items-center gap-3 text-sm">
        {canOpen ? (
          <Link
            href={openHref}
            className="text-accent-green underline-offset-4 hover:underline"
          >
            Open plan
          </Link>
        ) : (
          <span className="text-muted-foreground">Open plan unavailable</span>
        )}
        {canShare ? (
          <>
            <Link
              href={shareHref}
              className="text-accent-green underline-offset-4 hover:underline"
            >
              Share view
            </Link>
            <Button type="button" size="sm" variant="outline" onClick={() => void copyShare()}>
              {copied ? "Copied" : "Copy link"}
            </Button>
          </>
        ) : null}
      </div>
    </li>
  );
}

export function SavedTripsClient() {
  const { user, loading } = useAuth();
  const trips = useQuery({
    queryKey: ["trips", user?.id],
    enabled: Boolean(user),
    queryFn: () => listTrips(WARM_GENERATION_TIMEOUT_MS),
  });

  return (
    <main className="mx-auto max-w-2xl px-6 py-10">
      <h1 className="text-2xl font-semibold">Saved trips</h1>
      {loading ? (
        <p className="mt-4 text-sm text-muted-foreground">Checking your session…</p>
      ) : !user ? (
        <div className="mt-6 max-w-sm">
          <p className="mb-4 text-sm text-muted-foreground">
            Sign in to save and reopen trips. Anonymous planning still works from the home screen.
          </p>
          <LoginButtons />
        </div>
      ) : trips.isLoading ? (
        <p className="mt-4 text-sm text-muted-foreground">Loading saved trips…</p>
      ) : trips.isError ? (
        <p className="mt-4 text-sm text-accent-brown">
          {trips.error instanceof Error ? trips.error.message : "Could not load trips."}
        </p>
      ) : !trips.data?.trips.length ? (
        <p className="mt-4 text-sm text-muted-foreground">
          No saved trips yet. Generate an itinerary, then use Save in the itinerary panel.
        </p>
      ) : (
        <ul className="mt-6 space-y-3">
          {trips.data.trips
            .filter((trip) => trip.trip_id || trip.slug || trip.plan_id)
            .map((trip) => (
              <SavedTripCard key={trip.trip_id || trip.slug || trip.plan_id} trip={trip} />
            ))}
        </ul>
      )}
    </main>
  );
}
