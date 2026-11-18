import { QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { type ReactElement, StrictMode } from "react";
import { App } from "../App";
import { createQueryClient } from "../api/queryClient";

/** Render with a fresh query cache per test, so tests never share results. */
export function renderWithClient(ui: ReactElement) {
  const client = createQueryClient();
  return {
    user: userEvent.setup(),
    // StrictMode as in main.tsx: effects run twice, like in development.
    ...render(
      <StrictMode>
        <QueryClientProvider client={client}>{ui}</QueryClientProvider>
      </StrictMode>,
    ),
  };
}

/** Render the whole app as if the visitor had opened this address. */
export function renderApp(hash = "#/") {
  // `replaceState`: setting `location.hash` would fire a late `hashchange`,
  // which the home would take for a navigation in the middle of the test.
  window.history.replaceState(null, "", hash);
  return renderWithClient(<App />);
}

/**
 * Pretend the visitor scrolled the page to `y`: jsdom has no layout, so it
 * never scrolls by itself. Sets `window.scrollY` and fires the scroll event.
 */
export function scrollPageTo(y: number) {
  Object.defineProperty(window, "scrollY", { value: y, configurable: true });
  window.dispatchEvent(new Event("scroll"));
}
