/** The page of one Pokémon: how to beat it, then the encyclopedia. The API is faked by MSW. */
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { renderApp } from "../../test/render";
import { server } from "../../test/setup";
import { multiplier } from "../matchup/HowToBeat";

const title = (name: string) => screen.findByRole("heading", { level: 2, name });
const part = (name: string) => screen.findByRole("region", { name });
const fail = (path: string) =>
  server.use(
    http.get(path, () => HttpResponse.json({ detail: "boom" }, { status: 500 })),
  );

describe("Opening a page", () => {
  it("opens from a card of the catalog, at the top of the page", async () => {
    const { user } = renderApp();

    await user.click(await screen.findByRole("link", { name: "Pikachu" }));

    expect(await title("Pikachu")).toBeInTheDocument();
    expect(window.location.hash).toBe("#/pokemon/pikachu");
    expect(screen.getByText("#025")).toBeInTheDocument();
    expect(window.scrollTo).toHaveBeenLastCalledWith(0, 0);
  });

  it("opens from its address, with how to beat it before the encyclopedia", async () => {
    renderApp("#/pokemon/pikachu");

    const beat = await part("How to beat it");
    const about = await part("About");
    expect(
      beat.compareDocumentPosition(about) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(await within(about).findByText(/their electricity/)).toBeInTheDocument();
    expect(within(about).getByText("0.4 m")).toBeInTheDocument();
    expect(within(about).getByRole("row", { name: /Speed 90/ })).toBeInTheDocument();
    expect(within(about).getByText("lightning rod")).toBeInTheDocument();
    await waitFor(() =>
      expect(
        document.querySelector("header img[src$='artwork/25.png']"),
      ).not.toBeNull(),
    );
  });

  it("says when the Pokémon does not exist, with a way back", async () => {
    renderApp("#/pokemon/missingno");

    expect(await screen.findByText("Pokémon not found.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /All Pokémon/ })).toHaveAttribute(
      "href",
      "#/",
    );
    expect(screen.queryByRole("region", { name: "About" })).toBeNull();
  });
});

describe("How to beat it", () => {
  it("lists what to use, with the multipliers", async () => {
    renderApp("#/pokemon/bulbasaur");

    expect(await part("Use")).toHaveTextContent("fire×2ice×2flying×2psychic×2");
  });

  it("says when there is no weakness", async () => {
    renderApp("#/pokemon/mr-mime");

    expect(await part("Use")).toHaveTextContent("No weakness.");
  });

  it("lists what to avoid: immunities, resistances, protections, pitfalls", async () => {
    renderApp("#/pokemon/mr-mime");

    const avoid = await part("Avoid");
    expect(avoid).toHaveTextContent("dragon×0");
    expect(avoid).toHaveTextContent("ground×0 if its ability is levitate");
    expect(avoid).toHaveTextContent("grass×¼water×½");
    expect(avoid).toHaveTextContent("Immune to sleep (insomnia)");
    expect(avoid).toHaveTextContent(
      "Recovers from status conditions (natural cure, shed skin)",
    );
    expect(avoid).toHaveTextContent(
      "Avoid poisoning it: its ability synchronize can pass the status back to you.",
    );
    expect(avoid).toHaveTextContent(
      "Avoid inflicting a status condition on it: its ability guts makes it stronger.",
    );
  });

  it("lists what to watch out for: strong types and threats", async () => {
    renderApp("#/pokemon/bulbasaur");

    const watchOut = await part("Watch out");
    expect(watchOut).toHaveTextContent("Its types hit hard:watergrassgroundrockfairy");
    expect(watchOut).toHaveTextContent("Put to sleep (sleep powder)");
    expect(watchOut).toHaveTextContent("Poison (poison powder)");
  });

  it("leaves out a line with nothing to say", async () => {
    renderApp("#/pokemon/pikachu");

    expect(await part("Use")).toHaveTextContent("ground×2");
    expect(screen.queryByRole("region", { name: "Avoid" })).toBeNull();
    expect(screen.queryByRole("region", { name: "Watch out" })).toBeNull();
  });
});

describe("When a part cannot be loaded", () => {
  it("still shows how to beat it without the encyclopedia", async () => {
    fail("*/api/pokemon/:ref");
    renderApp("#/pokemon/pikachu");

    expect(await part("Use")).toHaveTextContent("ground×2");
    expect(await title("Pikachu")).toBeInTheDocument();
    expect(await part("About")).toHaveTextContent("Server error (500).");
  });

  it("still shows the header and the encyclopedia without the matchup", async () => {
    fail("*/api/pokemon/:ref/matchup");
    renderApp("#/pokemon/pikachu");

    expect(await title("Pikachu")).toBeInTheDocument();
    expect(screen.getByText("Mouse Pokémon")).toBeInTheDocument();
    expect(await part("How to beat it")).toHaveTextContent("Server error (500).");
    expect(await part("About")).toHaveTextContent(/their electricity/);
  });

  it("says so when nothing can be loaded, with a way back", async () => {
    fail("*/api/pokemon/:ref/matchup");
    fail("*/api/pokemon/:ref");
    renderApp("#/pokemon/pikachu");

    expect(await screen.findByRole("alert")).toHaveTextContent("Server error (500).");
    expect(screen.getByRole("link", { name: /All Pokémon/ })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "About" })).toBeNull();
  });
});

describe("Evolution family", () => {
  it("leads to the other members, not to the Pokémon on screen", async () => {
    const { user } = renderApp("#/pokemon/pikachu");

    const family = await part("Evolution family");
    expect(within(family).queryByRole("link", { name: "Pikachu" })).toBeNull();
    expect(within(family).getByText("Pikachu")).toHaveAttribute("aria-current", "page");
    await user.click(within(family).getByRole("link", { name: "Raichu" }));

    expect(await title("Raichu")).toBeInTheDocument();
    expect(await screen.findByText(/long tail/)).toBeInTheDocument();
    expect(window.scrollTo).toHaveBeenLastCalledWith(0, 0);
  });
});

describe("multiplier", () => {
  it("writes the usual fractions", () => {
    expect([4, 2, 1, 0.5, 0.25, 0].map(multiplier)).toEqual([
      "×4",
      "×2",
      "×1",
      "×½",
      "×¼",
      "×0",
    ]);
  });
});
