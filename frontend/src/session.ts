/**
 * What this browser tab remembers between the two screens. Plain module
 * variables, not React state: nothing re-renders when they change, they are
 * only read when a screen opens. Reset between tests (`test/setup.ts`).
 */
import { HOME_HREF } from "./navigation";

/** The last address of the home, with its search: where a page leads back. */
let lastHome = HOME_HREF;

/** Where the home was scrolled, and for which address. */
let lastScroll: { hash: string; y: number } | null = null;

export function rememberHome(href: string): void {
  lastHome = href;
}

/**
 * The way back from a page. Kept here (not read from the history) so that the
 * page's link leads to the same place as the browser's Back button.
 */
export const lastHomeHref = (): string => lastHome;

export function rememberScroll(hash: string, y: number): void {
  lastScroll = { hash, y };
}

/** Where to scroll the home for this address: back where it was, or the top. */
export const scrollFor = (hash: string): number =>
  lastScroll?.hash === hash ? lastScroll.y : 0;

export function resetSession(): void {
  lastHome = HOME_HREF;
  lastScroll = null;
}
