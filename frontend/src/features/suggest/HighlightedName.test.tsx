import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HighlightedName } from "./HighlightedName";

describe("HighlightedName", () => {
  it("puts the matched parts in bold", () => {
    const { container } = render(
      <HighlightedName
        segments={[
          { text: "Mr. ", matched: false },
          { text: "Mime", matched: true },
        ]}
      />,
    );

    const bold = container.querySelectorAll("strong");
    expect([...bold].map((el) => el.textContent)).toEqual(["Mime"]);
  });

  it("always shows the full name", () => {
    const { container } = render(
      <HighlightedName
        segments={[
          { text: "Nido", matched: true },
          { text: "ran♀", matched: false },
        ]}
      />,
    );

    expect(container.textContent).toBe("Nidoran♀");
  });

  it("shows nothing in bold for a fuzzy match (single unmatched segment)", () => {
    const { container } = render(
      <HighlightedName segments={[{ text: "Bulbasaur", matched: false }]} />,
    );

    expect(container.querySelector("strong")).toBeNull();
    expect(container.textContent).toBe("Bulbasaur");
  });
});
