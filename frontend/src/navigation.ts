import { useSyncExternalStore } from "react";

/**
 * The pages of the app. The current page is the part of the URL after `#`
 * (e.g. `/#/name`): the browser handles it alone, so the Back button and
 * shared links work without a routing library or any server configuration.
 */
export const PAGES = {
  home: "#/",
  catalog: "#/catalog",
  appearance: "#/appearance",
  name: "#/name",
  battle: "#/battle",
} as const;

export type Page = keyof typeof PAGES;

function subscribe(onChange: () => void) {
  window.addEventListener("hashchange", onChange);
  return () => window.removeEventListener("hashchange", onChange);
}

/** The page matching the URL; anything unknown is the home page. */
export function usePage(): Page {
  const hash = useSyncExternalStore(subscribe, () => window.location.hash);
  const page = (Object.keys(PAGES) as Page[]).find((key) => PAGES[key] === hash);
  return page ?? "home";
}
