import type { Page } from "@playwright/test";

import { icsBody, pdfDocument, PLAN_ID, planResult } from "./fixtures";

export async function mockPlannerApi(page: Page): Promise<void> {
  await page.route("**/health", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "ok", cache: "ok", db: "ok" }),
    });
  });

  await page.route("**/api/v1/plan", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        status: 202,
        contentType: "application/json",
        body: JSON.stringify({ plan_id: PLAN_ID, status: "queued" }),
      });
      return;
    }
    await route.fallback();
  });

  await page.route(`**/api/v1/plan/${PLAN_ID}/regenerate`, async (route) => {
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ plan_id: PLAN_ID, status: "queued" }),
    });
  });

  await page.route(`**/api/v1/plan/${PLAN_ID}/status**`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        plan_id: PLAN_ID,
        status: "complete",
        stage: "narrative_validate",
        progress: 100,
        resumable: false,
      }),
    });
  });

  await page.route(`**/api/v1/plan/${PLAN_ID}/export/ics`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/calendar",
      headers: { "Content-Disposition": 'attachment; filename="cuvoy-trip.ics"' },
      body: icsBody,
    });
  });

  await page.route(`**/api/v1/plan/${PLAN_ID}/export/pdf`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(pdfDocument),
    });
  });

  await page.route(`**/api/v1/plan/${PLAN_ID}`, async (route) => {
    if (route.request().url().includes("/export/") || route.request().url().includes("/status")) {
      await route.fallback();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(planResult),
    });
  });
}

export async function enterPlanner(page: Page): Promise<void> {
  await page.goto("/");
  await page.getByTestId("start-curating").click();
  await page.getByTestId("generate-plan").waitFor();
}

export async function generateMockPlan(page: Page): Promise<void> {
  await page.getByLabel("Trip request").fill("3 days in Bengaluru for museums and food");
  await page.getByLabel("Destination").fill("Bengaluru");
  await page.getByTestId("generate-plan").click();
  await page.getByTestId("itinerary-panel").getByText("Bangalore Palace").waitFor();
}
