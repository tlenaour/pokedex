/** Arriving on the app: choose a feature, get to it, come back. */
import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";
import { renderApp, renderWithClient } from "./test/render";

const choice = (name: string) => screen.getByRole("link", { name: new RegExp(name) });

describe("Home page", () => {
  it("offers the four features and shows none of them yet", () => {
    renderApp("home");

    expect(choice("Browse the Pokémon")).toBeInTheDocument();
    expect(choice("I saw a Pokémon and want to find its name")).toBeInTheDocument();
    expect(choice("I'm not sure of a Pokémon's name")).toBeInTheDocument();
    expect(choice("I want to beat a Pokémon")).toBeInTheDocument();
    expect(screen.queryByRole("combobox")).toBeNull();
    expect(screen.queryByRole("searchbox")).toBeNull();
    expect(screen.queryByRole("region", { name: "Catalog" })).toBeNull();
  });

  it("leads to the catalog", async () => {
    const { user } = renderApp("home");

    await user.click(choice("Browse the Pokémon"));

    expect(await screen.findByRole("region", { name: "Catalog" })).toBeInTheDocument();
    expect(await screen.findByText("3 Pokémon")).toBeInTheDocument();
  });

  it("leads to the search by appearance", async () => {
    const { user } = renderApp("home");

    await user.click(choice("I saw a Pokémon"));

    expect(
      await screen.findByRole("searchbox", {
        name: "Pokémon's appearance",
      }),
    ).toBeInTheDocument();
  });

  it("leads to the search by name", async () => {
    const { user } = renderApp("home");

    await user.click(choice("I'm not sure of"));

    expect(
      await screen.findByRole("combobox", { name: "Pokémon name" }),
    ).toBeInTheDocument();
  });

  it("leads to the fight preparation", async () => {
    const { user } = renderApp("home");

    await user.click(choice("I want to beat a Pokémon"));

    expect(
      await screen.findByRole("region", { name: "Prepare a battle" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Pokémon name" })).toBeInTheDocument();
  });

  it("comes back to the choice from a feature", async () => {
    const { user } = renderApp("name");

    await user.click(screen.getByRole("link", { name: /Change search/ }));

    expect(await screen.findByText("What do you want to do?")).toBeInTheDocument();
    expect(screen.queryByRole("combobox")).toBeNull();
  });

  it("shows the choice for an unknown address", () => {
    window.location.hash = "#/anything-else";
    renderWithClient(<App />);

    expect(screen.getByText("What do you want to do?")).toBeInTheDocument();
  });
});
