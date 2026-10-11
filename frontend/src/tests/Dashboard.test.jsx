import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import Dashboard from "../pages/Dashboard.jsx";

describe("Dashboard", () => {
  it("shows the empty state when analysis is missing", () => {
    render(
      <Dashboard
        data={{ mode: "offline", bills: [], analysis: null }}
        onRetry={vi.fn()}
      />
    );

    expect(
      screen.getByText("Let's look at your bills")
    ).toBeTruthy();
  });
});