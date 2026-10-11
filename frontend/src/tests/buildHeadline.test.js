import { describe, expect, it } from "vitest";
import { buildHeadline } from "../buildHeadline.js";

describe("buildHeadline", () => {
  it("handles missing analysis data", () => {
    const result = buildHeadline(null);

    expect(result.status).toBe("empty");
    expect(result.title).toBeTruthy();
    expect(result.message).toBeTruthy();
  });

  it("returns a normal headline for a normal month", () => {
    const analysis = {
      months: [
        {
          month: "2026-01",
          actual_units: 1200,
          status: "normal",
        },
      ],
      alerts: [],
    };

    const result = buildHeadline(analysis);

    expect(result.status).toBe("normal");
    expect(result.month).toBe("2026-01");
  });

  it("returns an alert headline for a flagged month", () => {
    const analysis = {
      months: [
        {
          month: "2026-01",
          actual_units: 1200,
          status: "normal",
        },
        {
          month: "2026-02",
          actual_units: 1700,
          status: "alert",
        },
      ],
      alerts: [
        {
          month: "2026-02",
          expected_monthly_saving: { inr: 1500 },
        },
      ],
    };

    const result = buildHeadline(analysis);

    expect(result.status).toBe("alert");
    expect(result.month).toBe("2026-02");
    expect(result.message).toContain("February");
  });

  it("uses the latest month regardless of array order", () => {
    const analysis = {
      months: [
        { month: "2026-02", actual_units: 1700, status: "watch" },
        { month: "2026-01", actual_units: 1200, status: "normal" },
      ],
      alerts: [],
    };

    const result = buildHeadline(analysis);

    expect(result.month).toBe("2026-02");
    expect(result.status).toBe("watch");
  });
});