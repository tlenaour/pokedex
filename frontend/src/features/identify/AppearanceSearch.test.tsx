/**
 * Identifying a Pokémon from what it looks like, from the trainer's point of
 * view. The API is faked by MSW.
 */
import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { receivedDescriptions } from "../../test/handlers";
import { renderApp } from "../../test/render";
import { server } from "../../test/setup";

const input = () => screen.getByRole("searchbox", { name: "Pokémon's appearance" });
const submit = () => screen.getByRole("button", { name: "Identify" });

describe("Identifying a Pokémon from its appearance", () => {
  it("shows the best match as a card and the others as a list", async () => {
    const { user } = renderApp("appearance");

    await user.type(input(), "small yellow mouse with red cheeks");
    await user.click(submit());

    const card = await screen.findByRole("region", {
      name: "Best match: Pikachu",
    });
    expect(within(card).getByText("Mouse Pokémon")).toBeInTheDocument();
    expect(within(card).getByText("electric")).toBeInTheDocument();
    const others = screen.getByRole("region", { name: "Other possibilities" });
    expect(
      within(others)
        .getAllByRole("listitem")
        .map((item) => item.textContent),
    ).toEqual([
      expect.stringContaining("Sandshrew"),
      expect.stringContaining("Voltorb"),
    ]);
  });

  it("opens the detailed card from the best match or from another possibility", async () => {
    const { user } = renderApp("appearance");
    await user.type(input(), "small yellow mouse with red cheeks{Enter}");

    await user.click(await screen.findByRole("button", { name: "Pikachu" }));
    const dialog = await screen.findByRole("dialog", { name: "Pikachu" });
    expect(await within(dialog).findByText(/their electricity/)).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Close" }));

    await user.click(screen.getByRole("button", { name: "Sandshrew" }));
    expect(
      await screen.findByRole("dialog", { name: "Sandshrew" }),
    ).toBeInTheDocument();
  });

  it("sends the request on submit only, with Enter too, trimmed", async () => {
    const { user } = renderApp("appearance");

    await user.type(input(), "  small yellow mouse with red cheeks  ");
    expect(receivedDescriptions).toEqual([]);
    await user.keyboard("{Enter}");

    await screen.findByRole("region", { name: /Best match/ });
    expect(receivedDescriptions).toEqual(["small yellow mouse with red cheeks"]);
  });

  it.each(["", "!!!"])("cannot submit %j (nothing to search)", async (text) => {
    const { user } = renderApp("appearance");

    if (text) await user.type(input(), text);

    expect(submit()).toBeDisabled();
  });

  it("limits the description to the backend's maximum length", () => {
    renderApp("appearance");
    expect(input()).toHaveAttribute("maxLength", "300");
  });

  it("says when nothing matches", async () => {
    const { user } = renderApp("appearance");

    await user.type(input(), "unknown thing{Enter}");

    expect(await screen.findByText("No Pokémon found.")).toBeInTheDocument();
  });

  it.each([
    [422, "Invalid description."],
    [503, "Search by appearance is unavailable right now."],
    [500, "Server error (500)."],
  ])("HTTP %i -> %s", async (status, message) => {
    server.use(
      http.get("*/api/pokemon/identify", () =>
        HttpResponse.json({ detail: "boom" }, { status }),
      ),
    );
    const { user } = renderApp("appearance");

    await user.type(input(), "yellow mouse{Enter}");

    expect(await screen.findByText(message)).toBeInTheDocument();
  });

  it("API unreachable", async () => {
    server.use(http.get("*/api/pokemon/identify", () => HttpResponse.error()));
    const { user } = renderApp("appearance");

    await user.type(input(), "yellow mouse{Enter}");

    expect(await screen.findByText(/API unreachable/)).toBeInTheDocument();
  });
});
