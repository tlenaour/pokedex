import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { type ReactElement, StrictMode } from "react";
import { App } from "../App";
import { PAGES, type Page } from "../navigation";

/** Render with a fresh query cache per test, so tests never share results. */
export function renderWithClient(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
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

/** Render the whole app as if the visitor had opened the URL of `page`. */
export function renderApp(page: Page) {
  window.location.hash = PAGES[page];
  return renderWithClient(<App />);
}

export const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/** The option whose text contains `text` (bold parts split its accessible name). */
export const findOption = (text: string) =>
  waitFor(() => {
    const option = screen
      .getAllByRole("option")
      .find((candidate) => candidate.textContent?.includes(text));
    if (!option) throw new Error(`No option containing ${text}`);
    return option;
  });
