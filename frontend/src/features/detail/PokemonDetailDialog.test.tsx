/** Opening the detailed card of a Pokémon from the catalog. The API is faked by MSW. */
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { renderApp } from "../../test/render";
import { server } from "../../test/setup";

const thumbnail = (name: string) => screen.findByRole("button", { name });
const card = (name: string) => screen.findByRole("dialog", { name });

describe("Detailed card of a Pokémon", () => {
  it("opens from a thumbnail of the catalog, with the details", async () => {
    const { user } = renderApp("catalog");

    await user.click(await thumbnail("Pikachu"));

    const dialog = await card("Pikachu");
    expect(within(dialog).getByText("#025")).toBeInTheDocument();
    expect(await within(dialog).findByText(/their electricity/)).toBeInTheDocument();
    expect(within(dialog).getByText("0.4 m")).toBeInTheDocument();
    expect(within(dialog).getByText("6 kg")).toBeInTheDocument();
    expect(within(dialog).getByText("forest")).toBeInTheDocument();
    expect(within(dialog).getByRole("row", { name: /Speed 90/ })).toBeInTheDocument();
    expect(within(dialog).getByRole("row", { name: /Total 320/ })).toBeInTheDocument();
    expect(within(dialog).getByText("lightning rod")).toBeInTheDocument();
    expect(within(dialog).getByRole("img", { name: "Pikachu" })).toHaveAttribute(
      "src",
      "https://example.com/artwork/25.png",
    );
  });

  it("shows what the catalog already knows while the details load", async () => {
    server.use(http.get("*/api/pokemon/:ref", () => new Promise(() => {})));
    const { user } = renderApp("catalog");

    await user.click(await thumbnail("Pikachu"));

    const dialog = await card("Pikachu");
    expect(within(dialog).getByText("Mouse Pokémon")).toBeInTheDocument();
    expect(within(dialog).getByText("Loading details…")).toBeInTheDocument();
  });

  it("closes with the close button", async () => {
    const { user } = renderApp("catalog");

    await user.click(await thumbnail("Pikachu"));
    await user.click(
      within(await card("Pikachu")).getByRole("button", { name: "Close" }),
    );

    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("goes to another Pokémon of the evolution family", async () => {
    const { user } = renderApp("catalog");

    await user.click(await thumbnail("Pikachu"));
    const dialog = await card("Pikachu");
    expect(
      await within(dialog).findByRole("button", { name: "Pikachu" }),
    ).toBeDisabled();
    await user.click(within(dialog).getByRole("button", { name: "Raichu" }));

    const raichu = await card("Raichu");
    expect(await within(raichu).findByText(/long tail/)).toBeInTheDocument();
  });

  it("says when the details cannot be loaded, keeping the card closable", async () => {
    server.use(
      http.get("*/api/pokemon/:ref", () =>
        HttpResponse.json({ detail: "boom" }, { status: 500 }),
      ),
    );
    const { user } = renderApp("catalog");

    await user.click(await thumbnail("Pikachu"));

    const dialog = await card("Pikachu");
    expect(await within(dialog).findByText("Server error (500).")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Close" })).toBeInTheDocument();
  });
});
