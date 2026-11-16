/**
 * "I did not find my Pokémon", from the results of both searches.
 * The API is faked by MSW.
 */
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { receivedReports } from "../../test/handlers";
import { renderApp } from "../../test/render";
import { server } from "../../test/setup";

const nameInput = () => screen.getByRole("combobox", { name: "Pokémon name" });
const appearanceInput = () =>
  screen.getByRole("searchbox", { name: "Pokémon's appearance" });
const reportLine = () => screen.findByRole("option", { name: /I didn't find/ });

describe("From the name search (last line of the list)", () => {
  it("reports the search and the Pokémon shown, keeping the typed text", async () => {
    const { user } = renderApp("name");

    await user.type(nameInput(), "nido");
    await reportLine();
    await user.keyboard("{ArrowDown}{ArrowDown}{ArrowDown}{Enter}");

    expect(await screen.findByText("Thanks, noted.")).toBeInTheDocument();
    expect(receivedReports).toEqual([
      { kind: "name", query: "nido", shown_ids: [29, 30] },
    ]);
    expect(nameInput()).toHaveValue("nido");
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("can report a search without any result", async () => {
    const { user } = renderApp("name");

    await user.type(nameInput(), "xyz");
    await user.click(await reportLine());

    await screen.findByText("Thanks, noted.");
    expect(receivedReports).toEqual([{ kind: "name", query: "xyz", shown_ids: [] }]);
  });

  it("reports a search only once, and again for the next search", async () => {
    const { user } = renderApp("name");

    await user.type(nameInput(), "xyz");
    await user.click(await reportLine());
    await user.click(await screen.findByText("Thanks, noted."));
    await user.clear(nameInput());
    await user.type(nameInput(), "bulba");
    await user.click(await reportLine());

    await screen.findByText("Thanks, noted.");
    expect(receivedReports.map((report) => report.query)).toEqual(["xyz", "bulba"]);
  });

  it("says when the report could not be sent, and lets the trainer retry", async () => {
    server.use(
      http.post("*/api/feedback/missing-result", () => HttpResponse.error(), {
        once: true,
      }),
    );
    const { user } = renderApp("name");

    await user.type(nameInput(), "xyz");
    await user.click(await reportLine());
    await user.click(
      await screen.findByRole("option", {
        name: /Could not send the report/,
      }),
    );

    await screen.findByText("Thanks, noted.");
    expect(receivedReports).toHaveLength(1);
  });
});

describe("From the appearance search (under the results)", () => {
  it("reports the description and the Pokémon shown", async () => {
    const { user } = renderApp("appearance");

    await user.type(appearanceInput(), "small yellow mouse with red cheeks{Enter}");
    await user.click(await screen.findByRole("button", { name: "Report" }));

    expect(await screen.findByText("Thanks, noted.")).toBeInTheDocument();
    expect(receivedReports).toEqual([
      {
        kind: "appearance",
        query: "small yellow mouse with red cheeks",
        shown_ids: [25, 27, 100],
      },
    ]);
  });

  it("can report a description without any result", async () => {
    const { user } = renderApp("appearance");

    await user.type(appearanceInput(), "unknown thing{Enter}");
    await user.click(await screen.findByRole("button", { name: "Report" }));

    await screen.findByText("Thanks, noted.");
    expect(receivedReports).toEqual([
      { kind: "appearance", query: "unknown thing", shown_ids: [] },
    ]);
  });

  it("offers to report again after a new search", async () => {
    const { user } = renderApp("appearance");

    await user.type(appearanceInput(), "unknown thing{Enter}");
    await user.click(await screen.findByRole("button", { name: "Report" }));
    await screen.findByText("Thanks, noted.");
    await user.clear(appearanceInput());
    await user.type(appearanceInput(), "small yellow mouse with red cheeks{Enter}");

    expect(await screen.findByRole("button", { name: "Report" })).toBeInTheDocument();
  });

  it("lets the trainer retry when the report could not be sent", async () => {
    server.use(
      http.post(
        "*/api/feedback/missing-result",
        () => HttpResponse.json({ detail: "boom" }, { status: 500 }),
        { once: true },
      ),
    );
    const { user } = renderApp("appearance");

    await user.type(appearanceInput(), "unknown thing{Enter}");
    await user.click(await screen.findByRole("button", { name: "Report" }));
    await user.click(await screen.findByRole("button", { name: "Retry" }));

    await screen.findByText("Thanks, noted.");
    expect(receivedReports).toHaveLength(1);
  });

  it("offers no report when the search itself failed", async () => {
    server.use(
      http.get("*/api/pokemon/identify", () =>
        HttpResponse.json({ detail: "no index" }, { status: 503 }),
      ),
    );
    const { user } = renderApp("appearance");

    await user.type(appearanceInput(), "yellow mouse{Enter}");
    await screen.findByText(/unavailable/);

    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Report" })).toBeNull(),
    );
  });
});
