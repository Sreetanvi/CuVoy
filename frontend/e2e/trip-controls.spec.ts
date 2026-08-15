import { expect, test } from "@playwright/test";

import { enterPlanner, generateMockPlan, mockPlannerApi } from "./helpers";

test.beforeEach(async ({ page }) => {
  await mockPlannerApi(page);
});

test("Trip Controls apply triggers a replan", async ({ page }) => {
  await enterPlanner(page);
  await generateMockPlan(page);
  await page.getByLabel("Pace").selectOption("packed");
  const regen = page.waitForRequest(
    (request) => request.url().includes("/regenerate") && request.method() === "POST",
  );
  await page.getByTestId("apply-trip-controls").click();
  const request = await regen;
  expect(request.postDataJSON().trip_controls.pace).toBe("packed");
  await expect(page.getByTestId("itinerary-panel")).toContainText("Bangalore Palace");
});
