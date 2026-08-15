import type { Metadata } from "next";

import { PlannerPage } from "@/components/planner/PlannerPage";

export const metadata: Metadata = {
  title: "Plan — CuVoy",
  robots: { index: false, follow: false },
};

export default async function PlanPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ trip?: string }>;
}) {
  const { id } = await params;
  const query = await searchParams;
  const savedTripId = query.trip?.trim() || undefined;
  return <PlannerPage planId={id} savedTripId={savedTripId} />;
}
