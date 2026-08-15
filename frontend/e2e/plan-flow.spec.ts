import { expect, test } from "@playwright/test";

import { enterPlanner, generateMockPlan, mockPlannerApi } from "./helpers";

test.beforeEach(async ({ page }) => {
  await mockPlannerApi(page);
});

test("landing to generated itinerary", async ({ page }) => {
  await enterPlanner(page);
  await expect(page.getByTestId("ai-disclaimer-footer")).toContainText(
    "Please verify important details before travel.",
  );
  await generateMockPlan(page);
  await expect(page.getByTestId("itinerary-panel")).toContainText("A walkable Bengaluru morning.");
  await expect(page.getByTestId("itinerary-panel")).toContainText("09:00");
});

test("privacy and disclaimer pages", async ({ page }) => {
  await page.goto("/privacy");
  await expect(page.getByTestId("privacy-page")).toContainText("GDPR");
  await page.goto("/disclaimer");
  await expect(page.getByTestId("ai-disclaimer-copy")).toContainText(
    "Please verify important details before travel.",
  );
});
