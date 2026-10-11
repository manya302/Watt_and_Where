import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import CommitteePreview from "../pages/CommitteePreview.jsx";

describe("CommitteePreview", () => {
  it("renders the committee preview page", () => {
    render(<CommitteePreview />);

    expect(
      document.body.textContent.trim().length
    ).toBeGreaterThan(0);
  });
});