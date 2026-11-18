import type { PokemonSummary } from "../../api/client";

const KEY = "pokedex.recent";
const MAX_RECENT = 5;

/** What is needed to show a link to a Pokémon without asking the API. */
export type RecentPokemon = Pick<PokemonSummary, "name" | "display_name" | "sprite">;

function isRecent(value: unknown): value is RecentPokemon {
  if (typeof value !== "object" || value === null) return false;
  const { name, display_name, sprite } = value as Record<string, unknown>;
  return (
    typeof name === "string" &&
    typeof display_name === "string" &&
    typeof sprite === "string"
  );
}

/**
 * The last Pokémon whose page was shown, most recent first.
 * A convenience only: storage that is unavailable (private browsing) or holds
 * something else gives an empty list, never an error.
 */
export function readRecent(): RecentPokemon[] {
  try {
    const stored: unknown = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(stored) ? stored.filter(isRecent).slice(0, MAX_RECENT) : [];
  } catch {
    return [];
  }
}

export function addRecent({ name, display_name, sprite }: RecentPokemon): void {
  const others = readRecent().filter((pokemon) => pokemon.name !== name);
  const next = [{ name, display_name, sprite }, ...others].slice(0, MAX_RECENT);
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // Not saved: the page works without it.
  }
}
