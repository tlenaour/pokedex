/** What the tab remembers between screens (src/session.ts). */
import { describe, expect, it } from "vitest";
import { HOME_HREF } from "./navigation";
import {
  lastHomeHref,
  rememberHome,
  rememberScroll,
  resetSession,
  scrollFor,
} from "./session";

describe("scroll position", () => {
  it("is given back for the address it was remembered for", () => {
    rememberScroll("#/?q=bulba", 640);

    expect(scrollFor("#/?q=bulba")).toBe(640);
  });

  it("is the top for any other address", () => {
    rememberScroll("#/?q=bulba", 640);

    expect(scrollFor("#/")).toBe(0);
    expect(scrollFor("#/?q=bulb")).toBe(0);
  });

  it("keeps only the last position", () => {
    rememberScroll("#/", 100);
    rememberScroll("#/", 900);

    expect(scrollFor("#/")).toBe(900);
  });
});

describe("resetSession", () => {
  it("forgets the scroll position and the way back", () => {
    rememberScroll("#/", 500);
    rememberHome("#/?q=nido");

    resetSession();

    expect(scrollFor("#/")).toBe(0);
    expect(lastHomeHref()).toBe(HOME_HREF);
  });
});
