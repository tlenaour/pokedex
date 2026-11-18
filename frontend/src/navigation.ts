import { useMemo, useSyncExternalStore } from "react";

/**
 * The screens of the app. The current one is the part of the URL after `#`
 * (e.g. `/#/pokemon/pikachu`): the browser handles it alone, so the Back
 * button and shared links work without a routing library or any server
 * configuration.
 */
export type Mode = "name" | "description";

export type Route =
  | { page: "home"; mode: Mode; q: string }
  | { page: "pokemon"; name: string };

const POKEMON_PREFIX = "#/pokemon/";

/** The screen matching a hash; anything unknown is the home, without search. */
export function parseRoute(hash: string): Route {
  if (hash.startsWith(POKEMON_PREFIX)) {
    const name = safeDecode(hash.slice(POKEMON_PREFIX.length));
    if (name && !name.includes("/")) return { page: "pokemon", name };
  }
  // Only `#/?...` carries a search: old addresses (`#/battle`) are the plain home.
  const params = new URLSearchParams(hash.startsWith("#/?") ? hash.slice(3) : "");
  return {
    page: "home",
    mode: params.get("mode") === "description" ? "description" : "name",
    q: params.get("q") ?? "",
  };
}

/** A hand-typed address may hold an invalid `%` sequence: not a reason to crash. */
function safeDecode(text: string): string {
  try {
    return decodeURIComponent(text);
  } catch {
    return "";
  }
}

export const HOME_HREF = "#/";

export const pokemonHref = (name: string) =>
  `${POKEMON_PREFIX}${encodeURIComponent(name)}`;

/** The home with its search, e.g. `#/?mode=description&q=yellow%20mouse`. */
export function homeHref(mode: Mode, q: string): string {
  const params = [
    mode === "description" ? "mode=description" : "",
    q ? `q=${encodeURIComponent(q)}` : "",
  ].filter(Boolean);
  return params.length > 0 ? `${HOME_HREF}?${params.join("&")}` : HOME_HREF;
}

function subscribe(onChange: () => void) {
  window.addEventListener("hashchange", onChange);
  return () => window.removeEventListener("hashchange", onChange);
}

/** The screen matching the URL, updated when the visitor navigates. */
export function useRoute(): Route {
  const hash = useSyncExternalStore(subscribe, () => window.location.hash);
  return useMemo(() => parseRoute(hash), [hash]);
}
