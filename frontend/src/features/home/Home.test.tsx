/**
 * The home from the visitor's point of view: one field above the catalog,
 * results in the grid, a card to open. The API is faked by MSW.
 */
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import {
  receivedDescriptions,
  receivedQueries,
  receivedReports,
} from "../../test/handlers";
import { renderApp, scrollPageTo } from "../../test/render";
import { server } from "../../test/setup";

const MOUSE = "small yellow mouse with red cheeks";

const field = () => screen.getByRole("searchbox");
const mode = (name: string) => screen.getByRole("radio", { name });
/** Names of the cards of a grid ("Catalog" or "Results"), in order. */
const cards = async (grid: string) =>
  within(await screen.findByRole("list", { name: grid }))
    .getAllByRole("article")
    .map((card) => card.getAttribute("aria-label"));
const card = (name: string) => screen.findByRole("article", { name });

describe("Catalog", () => {
  it("shows the whole Pokédex in order, without any click", async () => {
    renderApp();

    expect(await cards("Catalog")).toEqual(["Bulbasaur", "Pikachu", "Mr. Mime"]);
    expect(screen.getByText("3 Pokémon")).toBeInTheDocument();
    expect(mode("Name")).toBeChecked();
  });

  it("shows what is needed to recognize each Pokémon", async () => {
    renderApp();

    const mime = await card("Mr. Mime");
    expect(within(mime).getByText("#122")).toBeInTheDocument();
    expect(within(mime).getByText("Barrier Pokémon")).toBeInTheDocument();
    expect(within(mime).getByText("psychic")).toBeInTheDocument();
    expect(within(mime).getByRole("link", { name: "Mr. Mime" })).toHaveAttribute(
      "href",
      "#/pokemon/mr-mime",
    );
  });

  it("shows the home for an old address", async () => {
    renderApp("#/battle");

    expect(await cards("Catalog")).toHaveLength(3);
  });

  it("says when the catalog cannot be loaded", async () => {
    server.use(http.get("*/api/pokemon", () => HttpResponse.error()));
    renderApp();

    expect(await screen.findByText(/API unreachable/)).toBeInTheDocument();
  });
});

describe("Search by name", () => {
  it("replaces the grid with the API's results, the matching part in bold", async () => {
    const { user } = renderApp();
    await cards("Catalog");

    await user.type(field(), "nido");

    expect(await cards("Results")).toEqual(["Nidoran♀", "Nidorina"]);
    expect(screen.queryByRole("list", { name: "Catalog" })).toBeNull();
    expect(screen.getByText("2 results")).toBeInTheDocument();
    const nidorina = await card("Nidorina");
    expect(within(nidorina).getByText("Nido").tagName).toBe("STRONG");
    // Typed fast: one request, once the typing has stopped.
    expect(receivedQueries).toEqual(["nido"]);
  });

  it("marks a typo match as a guess", async () => {
    const { user } = renderApp();

    await user.type(field(), "bulbsaur");

    expect(await cards("Results")).toEqual(["Bulbasaur"]);
    expect(
      within(await card("Bulbasaur")).getByText("did you mean?"),
    ).toBeInTheDocument();
  });

  it("opens the first result with Enter", async () => {
    const { user } = renderApp();

    await user.type(field(), "nido");
    await cards("Results");
    await user.keyboard("{Enter}");

    await waitFor(() => expect(window.location.hash).toBe("#/pokemon/nidoran-f"));
  });

  it("opens the first result of the typed text when Enter comes before the answer", async () => {
    const { user } = renderApp();
    await user.type(field(), "nido");
    await cards("Results");

    await user.clear(field());
    await user.type(field(), "bulba{Enter}");

    await waitFor(() => expect(window.location.hash).toBe("#/pokemon/bulbasaur"));
    expect(
      await screen.findByRole("heading", { level: 2, name: "Bulbasaur" }),
    ).toBeInTheDocument();
  });

  it("shows the whole catalog again when the field is emptied", async () => {
    const { user } = renderApp();
    await user.type(field(), "bulba");
    await cards("Results");

    await user.clear(field());

    expect(await cards("Catalog")).toHaveLength(3);
  });

  it("offers the description search when nothing matches", async () => {
    const { user } = renderApp();

    await user.type(field(), "xyz");

    expect(await screen.findByText("No Pokémon found.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Try a description search" }));

    expect(mode("Description")).toBeChecked();
    expect(field()).toHaveValue("");
    expect(field()).toHaveFocus();
  });

  it("shows an error without breaking the page, and recovers", async () => {
    server.use(
      http.get("*/api/pokemon/suggest", () => HttpResponse.error(), { once: true }),
    );
    const { user } = renderApp();

    await user.type(field(), "nido");
    expect(await screen.findByText(/API unreachable/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Report" })).toBeNull();

    await user.clear(field());
    await user.type(field(), "bulba");

    expect(await cards("Results")).toEqual(["Bulbasaur"]);
    expect(screen.queryByText(/API unreachable/)).toBeNull();
  });
});

describe("Search by description", () => {
  it("searches on submit only, and marks the first result as the best match", async () => {
    const { user } = renderApp();
    await user.click(mode("Description"));

    await user.type(field(), `  ${MOUSE}  `);
    expect(receivedDescriptions).toEqual([]);
    expect(await cards("Catalog")).toHaveLength(3);
    await user.click(screen.getByRole("button", { name: "Search" }));

    expect(await cards("Results")).toEqual(["Pikachu", "Sandshrew", "Voltorb"]);
    expect(receivedDescriptions).toEqual([MOUSE]);
    expect(within(await card("Pikachu")).getByText("Best match")).toBeInTheDocument();
    expect(screen.getAllByText("Best match")).toHaveLength(1);
  });

  it("submits with Enter too", async () => {
    const { user } = renderApp();
    await user.click(mode("Description"));

    await user.type(field(), `${MOUSE}{Enter}`);

    expect(await cards("Results")).toHaveLength(3);
  });

  it("cannot submit a text with nothing to search", async () => {
    const { user } = renderApp();
    await user.click(mode("Description"));

    await user.type(field(), "!!!");

    expect(screen.getByRole("button", { name: "Search" })).toBeDisabled();
    expect(field()).toHaveAttribute("maxLength", "300");
  });

  it("says when nothing matches", async () => {
    const { user } = renderApp();
    await user.click(mode("Description"));

    await user.type(field(), "unknown thing{Enter}");

    expect(await screen.findByText("No Pokémon found.")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Try a description search" }),
    ).toBeNull();
  });

  it.each([
    [422, "Invalid description."],
    [503, "Search by appearance is unavailable right now."],
  ])("HTTP %i -> %s, without report line", async (status, message) => {
    server.use(
      http.get("*/api/pokemon/identify", () =>
        HttpResponse.json({ detail: "boom" }, { status }),
      ),
    );
    const { user } = renderApp();
    await user.click(mode("Description"));

    await user.type(field(), "yellow mouse{Enter}");

    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Report" })).toBeNull();
  });
});

describe("Changing mode", () => {
  it("empties the field and the results, and focuses the field", async () => {
    const { user } = renderApp();
    await user.type(field(), "bulba");
    await cards("Results");

    await user.click(mode("Description"));

    expect(field()).toHaveValue("");
    expect(field()).toHaveFocus();
    expect(field()).toHaveAttribute("placeholder", `e.g. ${MOUSE}`);
    expect(await cards("Catalog")).toHaveLength(3);
  });
});

describe("Clearing the search", () => {
  const clear = () => screen.queryByRole("button", { name: "Clear search" });

  it("is only offered when the field holds some text", async () => {
    const { user } = renderApp();
    expect(clear()).toBeNull();

    await user.type(field(), "b");

    expect(clear()).toBeInTheDocument();
  });

  it("brings the whole catalog back at once, in the search by name", async () => {
    const { user } = renderApp();
    await user.type(field(), "bulba");
    await cards("Results");

    await user.click(screen.getByRole("button", { name: "Clear search" }));

    expect(field()).toHaveValue("");
    expect(field()).toHaveFocus();
    expect(clear()).toBeNull();
    expect(await cards("Catalog")).toHaveLength(3);
    await waitFor(() => expect(window.location.hash).toBe("#/"));
  });

  it("also forgets a submitted description, and stays in that mode", async () => {
    const { user } = renderApp();
    await user.click(mode("Description"));
    await user.type(field(), `${MOUSE}{Enter}`);
    await cards("Results");

    await user.click(screen.getByRole("button", { name: "Clear search" }));

    expect(field()).toHaveValue("");
    expect(field()).toHaveFocus();
    expect(mode("Description")).toBeChecked();
    expect(await cards("Catalog")).toHaveLength(3);
    await waitFor(() => expect(window.location.hash).toBe("#/?mode=description"));
  });
});

describe("Reporting a missing Pokémon", () => {
  it("sends the name search and the Pokémon shown", async () => {
    const { user } = renderApp();
    await user.type(field(), "nido");

    await user.click(await screen.findByRole("button", { name: "Report" }));

    expect(await screen.findByText("Thanks, noted.")).toBeInTheDocument();
    expect(receivedReports).toEqual([
      { kind: "name", query: "nido", shown_ids: [29, 30] },
    ]);
  });

  it("sends a name search without any result", async () => {
    const { user } = renderApp();
    await user.type(field(), "xyz");

    await user.click(await screen.findByRole("button", { name: "Report" }));

    await screen.findByText("Thanks, noted.");
    expect(receivedReports).toEqual([{ kind: "name", query: "xyz", shown_ids: [] }]);
  });

  it("sends the description search and the Pokémon shown", async () => {
    const { user } = renderApp();
    await user.click(mode("Description"));
    await user.type(field(), `${MOUSE}{Enter}`);

    await user.click(await screen.findByRole("button", { name: "Report" }));

    await screen.findByText("Thanks, noted.");
    expect(receivedReports).toEqual([
      { kind: "appearance", query: MOUSE, shown_ids: [25, 27, 100] },
    ]);
  });

  it("offers a new report for the next search", async () => {
    const { user } = renderApp();
    await user.type(field(), "nido");
    await user.click(await screen.findByRole("button", { name: "Report" }));
    await screen.findByText("Thanks, noted.");

    await user.clear(field());
    await user.type(field(), "bulba");

    expect(await screen.findByRole("button", { name: "Report" })).toBeInTheDocument();
  });

  it("lets retry when the report could not be sent", async () => {
    server.use(
      http.post(
        "*/api/feedback/missing-result",
        () => HttpResponse.json({ detail: "boom" }, { status: 500 }),
        { once: true },
      ),
    );
    const { user } = renderApp();
    await user.type(field(), "nido");

    await user.click(await screen.findByRole("button", { name: "Report" }));
    await user.click(await screen.findByRole("button", { name: "Retry" }));

    await screen.findByText("Thanks, noted.");
    expect(receivedReports).toHaveLength(1);
  });
});

describe("The search lives in the URL", () => {
  it("opens a shared name search", async () => {
    renderApp("#/?q=bulba");

    expect(field()).toHaveValue("bulba");
    expect(await cards("Results")).toEqual(["Bulbasaur"]);
  });

  it("opens a shared description search", async () => {
    renderApp(`#/?mode=description&q=${encodeURIComponent(MOUSE)}`);

    expect(mode("Description")).toBeChecked();
    expect(field()).toHaveValue(MOUSE);
    expect(await cards("Results")).toHaveLength(3);
  });

  it("writes the search in the URL without adding history entries", async () => {
    const { user } = renderApp();
    const entries = window.history.length;

    await user.type(field(), "bulba");
    await cards("Results");

    expect(window.location.hash).toBe("#/?q=bulba");
    expect(window.history.length).toBe(entries);
  });

  it("finds the text and the results again when coming back from a page", async () => {
    const { user } = renderApp();
    await user.type(field(), "bulba");
    await cards("Results");

    await user.click(screen.getByRole("link", { name: "Bulbasaur" }));
    await screen.findByRole("heading", { level: 2, name: "Bulbasaur" });
    window.history.back();

    await waitFor(() => expect(screen.getByRole("searchbox")).toHaveValue("bulba"));
    expect(await cards("Results")).toEqual(["Bulbasaur"]);
  });

  it.each([
    ["the browser's Back button", () => window.history.back()],
    [
      "the link of the page",
      () => screen.getByRole("link", { name: /Back to results/ }).click(),
    ],
  ])("finds a description search again with %s", async (_, goBack) => {
    const { user } = renderApp();
    await user.click(mode("Description"));
    await user.type(field(), `${MOUSE}{Enter}`);
    await cards("Results");

    await user.click(screen.getByRole("link", { name: "Pikachu" }));
    await screen.findByRole("heading", { level: 2, name: "Pikachu" });
    goBack();

    await waitFor(() => expect(screen.getByRole("searchbox")).toHaveValue(MOUSE));
    expect(mode("Description")).toBeChecked();
    expect(await cards("Results")).toEqual(["Pikachu", "Sandshrew", "Voltorb"]);
  });

  it("goes back to the whole catalog with the header link", async () => {
    const { user } = renderApp("#/?q=bulba");
    await cards("Results");

    await user.click(screen.getByRole("link", { name: "Pokédex" }));

    await waitFor(() => expect(field()).toHaveValue(""));
    expect(await cards("Catalog")).toHaveLength(3);
  });
});

describe("Recently viewed", () => {
  it("lists the last pages shown, most recent first, without duplicate", async () => {
    const { user } = renderApp("#/pokemon/pikachu");
    await user.click(await screen.findByRole("link", { name: "Raichu" }));
    await screen.findByRole("heading", { level: 2, name: "Raichu" });
    await user.click(await screen.findByRole("link", { name: "Pikachu" }));
    await screen.findByRole("heading", { level: 2, name: "Pikachu" });

    await user.click(screen.getByRole("link", { name: /All Pokémon/ }));

    const recent = await screen.findByRole("navigation", { name: "Recently viewed" });
    const links = within(recent).getAllByRole("link");
    expect(links.map((link) => link.textContent)).toEqual(["Pikachu", "Raichu"]);
    expect(links[0]).toHaveAttribute("href", "#/pokemon/pikachu");
  });

  it("keeps five Pokémon at most, and keeps them on screen while searching", async () => {
    const viewed = ["a", "b", "c", "d", "e", "f"].map((name) => ({
      name,
      display_name: name.toUpperCase(),
      sprite: `https://example.com/${name}.png`,
    }));
    localStorage.setItem("pokedex.recent", JSON.stringify(viewed));
    const { user } = renderApp();

    const recent = screen.getByRole("navigation", { name: "Recently viewed" });
    expect(within(recent).getAllByRole("link")).toHaveLength(5);

    await user.type(field(), "bulba");
    await cards("Results");
    expect(
      screen.getByRole("navigation", { name: "Recently viewed" }),
    ).toBeInTheDocument();
  });

  it.each(["{not json", '"text"', '[{"name": 1}, null]'])(
    "ignores an unreadable storage (%s)",
    async (stored) => {
      localStorage.setItem("pokedex.recent", stored);
      renderApp();

      expect(await cards("Catalog")).toHaveLength(3);
      expect(screen.queryByRole("navigation", { name: "Recently viewed" })).toBeNull();
    },
  );
});

describe("Scroll position", () => {
  const lastScroll = () => vi.mocked(window.scrollTo).mock.lastCall;

  it("goes back where the grid was when coming back from a page", async () => {
    const { user } = renderApp();
    await cards("Catalog");
    scrollPageTo(1200);

    await user.click(screen.getByRole("link", { name: "Mr. Mime" }));
    await screen.findByRole("heading", { level: 2, name: "Mr. Mime" });
    expect(lastScroll()).toEqual([0, 0]); // the page opens at the top
    window.history.back();

    expect(await cards("Catalog")).toHaveLength(3);
    await waitFor(() => expect(lastScroll()).toEqual([0, 1200]));
  });

  it("remembers the position of each address separately", async () => {
    const { user } = renderApp();
    await user.type(field(), "bulba");
    await cards("Results");
    scrollPageTo(300);

    await user.click(screen.getByRole("link", { name: "Bulbasaur" }));
    await screen.findByRole("heading", { level: 2, name: "Bulbasaur" });
    // Another address than the one scrolled: the home starts at the top.
    window.location.hash = "#/?q=nido";

    expect(await cards("Results")).toEqual(["Nidoran♀", "Nidorina"]);
    await waitFor(() => expect(lastScroll()).toEqual([0, 0]));
  });

  it("restores once: later results do not move the page", async () => {
    const { user } = renderApp();
    await cards("Catalog");
    await waitFor(() => expect(window.scrollTo).toHaveBeenCalled());
    vi.mocked(window.scrollTo).mockClear();

    await user.type(field(), "bulba");
    await cards("Results");

    expect(window.scrollTo).not.toHaveBeenCalled();
  });
});
