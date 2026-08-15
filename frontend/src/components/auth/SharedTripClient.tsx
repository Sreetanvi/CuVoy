"use client";

import { WARM_GENERATION_TIMEOUT_MS } from "@cuvoy/contracts";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { PageFrame } from "@/components/layout/PageFrame";
import { PlannerPage } from "@/components/planner/PlannerPage";
import { PlanApiError } from "@/lib/planApi";
import { getSharedTrip } from "@/lib/tripApi";

export function SharedTripClient({ slug }: { slug: string }) {
  const query = useQuery({
    queryKey: ["shared-trip", slug],
    queryFn: () => getSharedTrip(slug, WARM_GENERATION_TIMEOUT_MS),
  });

  if (query.isLoading) {
    return (
      <PageFrame>
        <main className="mx-auto max-w-2xl px-6 py-12">
          <h1 className="text-2xl font-semibold">Shared trip</h1>
          <p className="mt-3 text-sm text-muted-foreground">Loading the read-only itinerary…</p>
        </main>
      </PageFrame>
    );
  }

  if (query.isError || !query.data) {
    const missing = query.error instanceof PlanApiError && query.error.status === 404;
    return (
      <PageFrame>
        <main className="mx-auto max-w-2xl px-6 py-12">
          <h1 className="text-2xl font-semibold">{missing ? "Trip not found" : "Could not load trip"}</h1>
          <p className="mt-3 text-sm text-muted-foreground">
            {missing
              ? "This share link is invalid or the trip was deleted."
              : query.error instanceof Error
                ? query.error.message
                : "Try again later."}
          </p>
          <Link href="/" className="mt-6 inline-block text-sm text-accent-green underline-offset-4 hover:underline">
            Open CuVoy
          </Link>
        </main>
      </PageFrame>
    );
  }

  return (
    <PlannerPage
      initialResult={query.data.result}
      readOnly
      shareTitle={query.data.trip.title}
    />
  );
}
