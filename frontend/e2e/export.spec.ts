import { expect, test } from "@playwright/test";

import { enterPlanner, generateMockPlan, mockPlannerApi } from "./helpers";

test.beforeEach(async ({ page }) => {
  await mockPlannerApi(page);
});

test("ICS and PDF export after a plan", async ({ page }) => {
  await enterPlanner(page);
  await generateMockPlan(page);

  const icsDownload = page.waitForEvent("download");
  await page.getByTestId("ics-download").click();
  const ics = await icsDownload;
  expect(ics.suggestedFilename()).toBe("cuvoy-trip.ics");

  const pdfDownload = page.waitForEvent("download");
  await page.getByTestId("pdf-export").click();
  const pdf = await pdfDownload;
  expect(pdf.suggestedFilename()).toBe("cuvoy-trip.pdf");
});
