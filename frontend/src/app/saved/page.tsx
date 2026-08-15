import type { Metadata } from "next";

import { SavedTripsClient } from "@/components/auth/SavedTripsClient";
import { PageFrame } from "@/components/layout/PageFrame";

export const metadata: Metadata = {
  title: "Saved trips — CuVoy",
  robots: { index: false, follow: false },
};

export default function SavedPage() {
  return (
    <PageFrame>
      <SavedTripsClient />
    </PageFrame>
  );
}
