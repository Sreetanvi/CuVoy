import { AI_DISCLAIMER } from "@cuvoy/contracts";
import type { Metadata } from "next";
import Link from "next/link";

import { PageFrame } from "@/components/layout/PageFrame";

export const metadata: Metadata = {
  title: "Privacy — CuVoy",
};

export default function PrivacyPage() {
  return (
    <PageFrame>
      <main className="mx-auto max-w-2xl px-6 py-12" data-testid="privacy-page">
        <p className="mb-8 text-sm">
          <Link href="/" className="text-accent-green underline-offset-4 hover:underline">
            Back to CuVoy
          </Link>
        </p>
        <h1 className="text-3xl font-semibold">Privacy policy</h1>
        <div className="mt-6 space-y-4 text-sm leading-6 text-muted-foreground">
          <p>
            CuVoy lets you plan anonymously. We do not require an account to generate an itinerary.
            Saving or sharing a trip requires sign-in (email or Google via Supabase Auth).
          </p>
          <h2 className="pt-2 text-base font-medium text-foreground">What we collect</h2>
          <ul className="list-disc space-y-2 pl-5">
            <li>Trip prompts, dates, destination, and Trip Controls you submit to the planner.</li>
            <li>
              A daily plan-credit identity (signed-in account, or IP / browser fingerprint when
              anonymous) so we can enforce 3 plans per day.
            </li>
            <li>Account email and auth tokens if you sign in to save, share, or delete data.</li>
            <li>Saved trip content you choose to store, including a share slug if you publish one.</li>
          </ul>
          <h2 className="pt-2 text-base font-medium text-foreground">How we use it</h2>
          <p>
            Planning runs on our FastAPI backend. The browser does not call place, weather, or LLM
            providers directly. Map rendering uses Mapbox in the client and shows Mapbox
            attribution on the map. We use your request only to build, cache, and (if you save)
            persist an itinerary. We do not sell personal data.
          </p>
          <h2 className="pt-2 text-base font-medium text-foreground">GDPR (basic)</h2>
          <p>
            Logged-in users own their trips. Saving a trip is explicit consent to store that
            itinerary on your account. You can delete your account and saved trip data from{" "}
            <Link href="/account" className="text-accent-green underline-offset-4 hover:underline">
              profile settings
            </Link>
            . Session data for an unsaved plan is temporary.
          </p>
          <p>
            API keys never ship in this repository. Production secrets live in Vercel and the
            Render dashboard only.
          </p>
          <p>
            See the{" "}
            <Link href="/disclaimer" className="text-accent-green underline-offset-4 hover:underline">
              AI disclaimer
            </Link>{" "}
            for how estimates are labeled. {AI_DISCLAIMER}
          </p>
        </div>
      </main>
    </PageFrame>
  );
}
