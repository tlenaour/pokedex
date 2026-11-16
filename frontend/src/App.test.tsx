/**
 * The feature from the trainer's point of view: type the beginning of a name,
 * recognize the Pokémon, select it to confirm. The API is faked by MSW.
 */
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { DEBOUNCE_MS } from "./features/suggest/useSuggestions";
import { receivedQueries } from "./test/handlers";
import { findOption, renderApp, wait } from "./test/render";
import { server } from "./test/setup";

const input = () => screen.getByRole("combobox", { name: "Pokémon name" });

describe("Finding a Pokémon from a partially remembered name", () => {
  it("suggests Bulbasaur for 'bulba', with what is needed to recognize it", async () => {
    const { user } = renderApp("name");

    await user.type(input(), "bulba");

    const option = await findOption("Bulbasaur");
    expect(within(option).getByText("Bulba").tagName).toBe("STRONG");
    expect(within(option).getByText("grass")).toBeInTheDocument();
    expect(within(option).getByText("poison")).toBeInTheDocument();
    expect(within(option).getByText("Seed Pokémon")).toBeInTheDocument();
    expect(option.querySelector("img")).toHaveAttribute(
      "src",
      "https://example.com/sprites/1.png",
    );
  });

  it("sends a single request when typing fast (debounce)", async () => {
    const { user } = renderApp("name");

    await user.type(input(), "bulba");
    await findOption("Bulbasaur");

    expect(receivedQueries).toEqual(["bulba"]);
  });

  it.each(["!!!", "   "])(
    "sends no request for %j (nothing to search)",
    async (text) => {
      const { user } = renderApp("name");

      await user.type(input(), text);
      await wait(DEBOUNCE_MS + 100);

      expect(receivedQueries).toEqual([]);
      expect(screen.queryByRole("option")).not.toBeInTheDocument();
    },
  );

  it("highlights the display name, not the slug (Mr. Mime)", async () => {
    const { user } = renderApp("name");

    await user.type(input(), "mime");

    const option = await screen.findByRole("option", { name: /Mr\. Mime/ });
    expect(within(option).getByText("Mime").tagName).toBe("STRONG");
  });

  it("says when nothing matches", async () => {
    const { user } = renderApp("name");

    await user.type(input(), "xyz");

    expect(await screen.findByText("No Pokémon found.")).toBeInTheDocument();
    // Only the report line: the trainer can say what they were looking for is missing.
    expect(screen.getAllByRole("option").map((o) => o.textContent)).toEqual([
      "I didn't find my Pokémon",
    ]);
  });

  it("marks a typo match as a guess, without bold", async () => {
    const { user } = renderApp("name");

    await user.type(input(), "bulbsaur");

    const option = await findOption("Bulbasaur");
    expect(within(option).getByText("did you mean?")).toBeInTheDocument();
    expect(option.querySelector("strong")).toBeNull();
  });

  it("selects with the keyboard and opens the detailed card", async () => {
    const { user } = renderApp("name");

    await user.type(input(), "nido");
    expect(await screen.findAllByRole("option")).toHaveLength(3); // 2 + report line
    await user.keyboard("{ArrowDown}{ArrowDown}{Enter}");

    const dialog = await screen.findByRole("dialog", { name: "Nidorina" });
    expect(within(dialog).getByText("Poison Pin Pokémon")).toBeInTheDocument();
  });

  it("keeps the typed text and the suggestions behind the card", async () => {
    const { user } = renderApp("name");

    await user.type(input(), "nido");
    await user.click(await findOption("Nidorina"));
    const dialog = await screen.findByRole("dialog", { name: "Nidorina" });
    await user.click(within(dialog).getByRole("button", { name: "Close" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());

    expect(input()).toHaveValue("nido");
    expect(screen.getAllByRole("option")).toHaveLength(3); // 2 + report line

    // The same Pokémon can be opened again, or another one.
    await user.click(await findOption("Nidorina"));
    expect(await screen.findByRole("dialog", { name: "Nidorina" })).toBeInTheDocument();
  });
});

describe("Errors are shown, never crash the page", () => {
  it.each([
    [422, "Invalid search."],
    [500, "Server error (500)."],
  ])("HTTP %i -> %s", async (status, message) => {
    server.use(
      http.get("*/api/pokemon/suggest", () =>
        HttpResponse.json({ detail: "boom" }, { status }),
      ),
    );
    const { user } = renderApp("name");

    await user.type(input(), "bulba");

    expect(await screen.findByText(message)).toBeInTheDocument();
  });

  it("API unreachable", async () => {
    server.use(http.get("*/api/pokemon/suggest", () => HttpResponse.error()));
    const { user } = renderApp("name");

    await user.type(input(), "bulba");

    expect(await screen.findByText(/API unreachable/)).toBeInTheDocument();
  });

  it("recovers on the next query after an error", async () => {
    server.use(
      http.get("*/api/pokemon/suggest", () => HttpResponse.error(), { once: true }),
    );
    const { user } = renderApp("name");

    await user.type(input(), "xyz");
    await screen.findByText(/API unreachable/);
    await user.clear(input());
    await user.type(input(), "bulba");

    await waitFor(() =>
      expect(screen.getAllByRole("option")[0]).toHaveTextContent("Bulbasaur"),
    );
    expect(screen.queryByText(/API unreachable/)).not.toBeInTheDocument();
  });
});
