import type { Metadata } from "next";

import { SharedTripClient } from "@/components/auth/SharedTripClient";

export const metadata: Metadata = {
  title: "Shared trip — CuVoy",
  robots: { index: false, follow: false },
};

export default async function SharedTripPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <SharedTripClient slug={slug} />;
}
