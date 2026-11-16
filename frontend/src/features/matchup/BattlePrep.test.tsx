/** Preparing a fight: choose the opponent, read its weak points and its threats. */
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { findOption, renderApp } from "../../test/render";
import { server } from "../../test/setup";
import { multiplier } from "./BattlePrep";

async function chooseOpponent(text: string, name: string) {
  const view = renderApp("battle");
  await view.user.type(screen.getByRole("combobox", { name: "Pokémon name" }), text);
  await view.user.click(await findOption(name));
  return view;
}

const group = (title: string) => screen.getByRole("region", { name: title });

describe("Prepare a battle", () => {
  it("shows the weaknesses and strengths of the chosen Pokémon", async () => {
    await chooseOpponent("bulba", "Bulbasaur");

    expect(
      screen.getByRole("region", { name: "Opponent: Bulbasaur" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Pokémon name" })).toHaveValue(
      "Bulbasaur",
    );
    expect(
      await screen.findByRole("region", { name: "Weak against" }),
    ).toHaveTextContent("fire×2ice×2flying×2psychic×2");
    expect(group("Resists")).toHaveTextContent("grass×¼water×½");
    expect(group("Strong against")).toHaveTextContent("watergrassgroundrockfairy");
    expect(group("Immune to")).toHaveTextContent("No immunity.");
  });

  it("says when an immunity only comes from a possible ability", async () => {
    await chooseOpponent("mime", "Mr. Mime");

    const immunities = await screen.findByRole("region", { name: "Immune to" });
    expect(immunities).toHaveTextContent("dragon");
    expect(immunities).toHaveTextContent("groundif its ability is levitate");
    expect(group("Weak against")).toHaveTextContent("No weakness.");
  });

  it("lists what the opponent can inflict", async () => {
    await chooseOpponent("bulba", "Bulbasaur");

    const threats = await screen.findByRole("region", {
      name: "What it can inflict on you",
    });
    expect(threats).toHaveTextContent("Put to sleep (sleep powder)");
    expect(threats).toHaveTextContent("Poison (poison powder)");
    expect(screen.queryByRole("region", { name: "What to avoid" })).toBeNull();
    expect(
      screen.queryByRole("region", { name: "What it can avoid or cure" }),
    ).toBeNull();
  });

  it("lists what the opponent can avoid or heal", async () => {
    await chooseOpponent("mime", "Mr. Mime");

    const protections = await screen.findByRole("region", {
      name: "What it can avoid or cure",
    });
    expect(protections).toHaveTextContent("Immune to sleep (insomnia)");
    expect(protections).toHaveTextContent(
      "Recovers from status conditions (natural cure, shed skin)",
    );
  });

  it("warns about what not to do to the opponent", async () => {
    await chooseOpponent("mime", "Mr. Mime");

    const pitfalls = await screen.findByRole("region", { name: "What to avoid" });
    expect(pitfalls).toHaveTextContent(
      "Avoid poisoning it: its ability synchronize can pass the status back to you.",
    );
    expect(pitfalls).toHaveTextContent(
      "Avoid inflicting a status condition on it: its ability guts makes it stronger.",
    );
    expect(
      screen.getByRole("region", { name: "What it can inflict on you" }),
    ).toHaveTextContent("Nothing in particular.");
  });

  it("shows an error without breaking the page", async () => {
    server.use(
      http.get("*/api/pokemon/:ref/matchup", () =>
        HttpResponse.json({ detail: "boom" }, { status: 500 }),
      ),
    );
    await chooseOpponent("bulba", "Bulbasaur");

    expect(await screen.findByRole("alert")).toHaveTextContent("Server error (500).");
    expect(screen.getByRole("combobox", { name: "Pokémon name" })).toBeInTheDocument();
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
