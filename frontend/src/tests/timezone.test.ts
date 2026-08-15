import { describe, expect, it } from "vitest";

import { clockFromLocal } from "@/lib/format";
import { clockPortion, displayLocalTime, displayLocalTimeOnly } from "@/lib/timezone";

describe("destination-local display", () => {
  it("never converts a local clock into another zone", () => {
    expect(displayLocalTime("2026-04-10T09:00:00", "Asia/Tokyo")).toBe(
      "2026-04-10T09:00:00 (Asia/Tokyo)",
    );
    expect(displayLocalTimeOnly("2026-04-10T09:00:00")).toBe("2026-04-10T09:00:00");
    expect(clockPortion("2026-04-10T14:30:00")).toBe("14:30");
    expect(clockFromLocal({ timezone: "Europe/Paris", local_time: "2026-04-10T09:15:00" })).toBe(
      "09:15",
    );
  });
});
