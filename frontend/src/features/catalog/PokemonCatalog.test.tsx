/** The Pokédex presented as a product catalog. The API is faked by MSW. */
import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { renderApp } from "../../test/render";
import { server } from "../../test/setup";

const catalog = () => screen.getByRole("region", { name: "Catalog" });

describe("Catalog", () => {
  it("shows every Pokémon, in Pokédex order", async () => {
    renderApp("catalog");

    expect(await within(catalog()).findByText("3 Pokémon")).toBeInTheDocument();
    expect(
      within(catalog())
        .getAllByRole("article")
        .map((item) => item.getAttribute("aria-label")),
    ).toEqual(["Bulbasaur", "Pikachu", "Mr. Mime"]);
  });

  it("shows what is needed to recognize each Pokémon", async () => {
    renderApp("catalog");

    const item = await within(catalog()).findByRole("article", { name: "Mr. Mime" });
    expect(within(item).getByText("#122")).toBeInTheDocument();
    expect(within(item).getByText("Barrier Pokémon")).toBeInTheDocument();
    expect(within(item).getByText("psychic")).toBeInTheDocument();
    expect(within(item).getByText("fairy")).toBeInTheDocument();
    const picture = item.querySelector("img");
    expect(picture).toHaveAttribute("src", "https://example.com/sprites/122.png");
    expect(picture).toHaveAttribute("loading", "lazy");
  });

  it("lays out up to 5 Pokémon per row on large screens", async () => {
    renderApp("catalog");

    const item = await within(catalog()).findByRole("article", { name: "Pikachu" });
    // jsdom computes no layout: check the grid classes instead.
    expect(item.closest("ul")).toHaveClass("grid", "grid-cols-2", "lg:grid-cols-5");
  });

  it("says when the catalog cannot be loaded, without breaking the searches", async () => {
    server.use(http.get("*/api/pokemon", () => HttpResponse.error()));
    const { user } = renderApp("catalog");

    expect(await within(catalog()).findByText(/API unreachable/)).toBeInTheDocument();
    // The searches are one click away: back to the choice, then the search.
    await user.click(screen.getByRole("link", { name: /Change search/ }));
    await user.click(await screen.findByRole("link", { name: /not sure of/ }));
    expect(
      await screen.findByRole("combobox", { name: "Pokémon name" }),
    ).toBeInTheDocument();
  });

  it("says when the Pokédex is empty", async () => {
    server.use(http.get("*/api/pokemon", () => HttpResponse.json([])));
    renderApp("catalog");

    expect(
      await within(catalog()).findByText("The Pokédex is empty."),
    ).toBeInTheDocument();
  });
});
