import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll } from "vitest";
import {
  handlers,
  receivedDescriptions,
  receivedQueries,
  receivedReports,
} from "./handlers";

// jsdom knows the <dialog> element but not its methods: the minimum to open
// and close one. A browser also traps focus and handles Escape by itself.
HTMLDialogElement.prototype.showModal = function () {
  this.setAttribute("open", "");
};
HTMLDialogElement.prototype.close = function () {
  if (!this.hasAttribute("open")) return;
  this.removeAttribute("open");
  this.dispatchEvent(new Event("close"));
};

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
  // Each test starts from the page it asks for, not the previous test's.
  window.location.hash = "";
});
afterAll(() => server.close());
