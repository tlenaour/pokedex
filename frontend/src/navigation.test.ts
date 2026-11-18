import { describe, expect, it } from "vitest";
import { homeHref, parseRoute, pokemonHref } from "./navigation";

describe("parseRoute", () => {
  it.each(["", "#", "#/"])("reads %j as the home without search", (hash) => {
    expect(parseRoute(hash)).toEqual({ page: "home", mode: "name", q: "" });
  });

  it("reads a search by name", () => {
    expect(parseRoute("#/?q=bulba")).toEqual({
      page: "home",
      mode: "name",
      q: "bulba",
    });
  });

  it("reads a search by description", () => {
    expect(parseRoute("#/?mode=description&q=yellow%20mouse")).toEqual({
      page: "home",
      mode: "description",
      q: "yellow mouse",
    });
  });

  it("takes an unknown mode for the search by name", () => {
    expect(parseRoute("#/?mode=color&q=red")).toEqual({
      page: "home",
      mode: "name",
      q: "red",
    });
  });

  it("reads the page of a Pokémon", () => {
    expect(parseRoute("#/pokemon/mr-mime")).toEqual({
      page: "pokemon",
      name: "mr-mime",
    });
  });

  it.each([
    "#/battle",
    "#/catalog",
    "#/pokemon/",
    "#/pokemon/a/b",
    "#/pokemon/%E0%A4%A",
  ])("reads %j as the home", (hash) => {
    expect(parseRoute(hash).page).toBe("home");
  });
});

describe("links", () => {
  it("round-trip through parseRoute", () => {
    expect(parseRoute(pokemonHref("mr-mime"))).toEqual({
      page: "pokemon",
      name: "mr-mime",
    });
    expect(parseRoute(homeHref("description", "yellow mouse & co"))).toEqual({
      page: "home",
      mode: "description",
      q: "yellow mouse & co",
    });
  });

  it("writes the shortest address", () => {
    expect(homeHref("name", "")).toBe("#/");
    expect(homeHref("name", "bulba")).toBe("#/?q=bulba");
    expect(homeHref("description", "yellow mouse")).toBe(
      "#/?mode=description&q=yellow%20mouse",
    );
  });
});
