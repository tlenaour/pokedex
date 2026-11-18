import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, vi } from "vitest";
import { resetSession } from "../session";
import {
  handlers,
  receivedDescriptions,
  receivedQueries,
  receivedReports,
} from "./handlers";

// jsdom has no layout, so it cannot scroll: tests only check the calls.
window.scrollTo = vi.fn();

/** Fake backend at the network level: the app's real fetch code runs. */
export const server = setupServer(...handlers);

// Any request without a handler fails the test (no silent real call).
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  cleanup();
  server.resetHandlers();
  receivedQueries.length = 0;
  receivedDescriptions.length = 0;
  receivedReports.length = 0;
  vi.mocked(window.scrollTo).mockClear();
  // Tests may pretend the page was scrolled (see scrollPageTo in test/render.tsx).
  Object.defineProperty(window, "scrollY", { value: 0, configurable: true });
  localStorage.clear();
  resetSession();
  // Each test starts from the page it asks for, not the previous test's.
  // `replaceState`: no `hashchange` left to fire during the next test.
  window.history.replaceState(null, "", "#/");
});
afterAll(() => server.close());
