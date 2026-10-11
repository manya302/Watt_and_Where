import { describe, expect, it } from "vitest";
import { isOfflineMode } from "../api.js";

describe("API configuration", () => {
  it("exports the offline mode checker", () => {
    expect(typeof isOfflineMode).toBe("function");
  });
});