import { AI_DISCLAIMER, COST_LABEL_UI } from "@cuvoy/contracts";
import type { Metadata } from "next";
import Link from "next/link";

import { PageFrame } from "@/components/layout/PageFrame";

export const metadata: Metadata = {
  title: "AI disclaimer — CuVoy",
};

export default function DisclaimerPage() {
  return (
    <PageFrame>
      <main className="mx-auto max-w-2xl px-6 py-12" data-testid="disclaimer-page">
        <p className="mb-8 text-sm">
          <Link href="/" className="text-accent-green underline-offset-4 hover:underline">
            Back to CuVoy
          </Link>
        </p>
        <h1 className="text-3xl font-semibold">AI disclaimer</h1>
        <div className="mt-6 space-y-4 text-sm leading-6 text-muted-foreground">
          <p data-testid="ai-disclaimer-copy">{AI_DISCLAIMER}</p>
          <p>
            CuVoy is a planner, not a booking engine. The language model ranks and narrates. Mapbox
            routes. Deterministic code validates hours, geography, and costs. The model does not
            invent places, coordinates, opening hours, travel times, or factual prices.
          </p>
          <h2 className="pt-2 text-base font-medium text-foreground">Cost labels</h2>
          <ul className="list-disc space-y-2 pl-5">
            <li>
              <span className="text-foreground">{COST_LABEL_UI.verified_fare}</span> — a published
              fare or ticket we could confirm.
            </li>
            <li>
              <span className="text-foreground">{COST_LABEL_UI.estimated_cost}</span> — a formula or
              typical range, not a live quote.
            </li>
            <li>
              <span className="text-foreground">{COST_LABEL_UI.unavailable}</span> — we will not
              guess. Transport cost stays off until you opt in.
            </li>
          </ul>
          <p>
            Read the{" "}
            <Link href="/privacy" className="text-accent-green underline-offset-4 hover:underline">
              privacy policy
            </Link>{" "}
            for what we store and how to delete it.
          </p>
        </div>
      </main>
    </PageFrame>
  );
}
