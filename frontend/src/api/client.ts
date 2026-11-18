import createClient from "openapi-fetch";
import type { components, paths } from "./schema";

// Absolute URL: the browser resolves it against the page, and tests (Node's
// fetch, which rejects relative URLs) get jsdom's origin.
export const api = createClient<paths>({
  baseUrl: `${window.location.origin}/api`,
  // Look `fetch` up at each call: openapi-fetch would otherwise keep the one
  // present when this module loads, before tools that wrap it (MSW in tests).
  fetch: (request) => globalThis.fetch(request),
});

// Response types come from the backend's OpenAPI schema: never written by hand.
// Regenerate them with `pnpm gen:api` after a backend change.
type Schemas = components["schemas"];
export type PokemonSuggestion = Schemas["PokemonSuggestionOut"];
export type NameSegment = Schemas["NameSegmentOut"];
export type PokemonType = Schemas["PokemonType"];
export type PokemonIdentification = Schemas["PokemonIdentificationOut"];
export type MissingResultReport = Schemas["MissingResultReportIn"];

/** A Pokémon as listed in the catalog: enough to recognize it. Suggestions
 * and identifications have the same fields (plus their own). */
export type PokemonSummary = Schemas["PokemonSummary"];

/** Everything about one Pokémon (GET /pokemon/{ref}): the detailed card. */
export type PokemonDetail = Schemas["PokemonOut"];

/** How to fight a Pokémon (GET /pokemon/{ref}/matchup). */
export type Matchup = Schemas["MatchupOut"];
export type Effect = Schemas["Effect"];
export type Pitfall = Schemas["PitfallOut"];
export type Protection = Schemas["ProtectionOut"];

/** An error to show to the user, already worded for them. */
export class ApiError extends Error {}

/** The Pokémon asked for does not exist (404): the page says so, with a way out. */
export class NotFoundError extends ApiError {
  constructor() {
    super("Pokémon not found.");
  }
}

/**
 * Run one API request and return its data, or throw an error already worded
 * for the user. Every data hook goes through here: one error policy.
 *
 * - a cancelled request (outdated query) is rethrown as is: not an error to show;
 * - no answer at all → "API unreachable";
 * - 404 → NotFoundError (the only 404s the frontend can get are Pokémon
 *   references; the API also answers 404 on /moves/{ref} and /abilities/{ref});
 * - other failures → the call's own message for that status if it has one,
 *   otherwise "Server error (N)".
 */
export async function call<T>(
  request: Promise<{ data?: T; response: Response }>,
  messages: Partial<Record<number, string>> = {},
): Promise<T> {
  const { data, response } = await request.catch((error: unknown) => {
    if (error instanceof Error && error.name === "AbortError") throw error;
    throw new ApiError("API unreachable. Check that the server is running.");
  });
  if (response.status === 404) throw new NotFoundError();
  if (!response.ok || data === undefined) {
    throw new ApiError(
      messages[response.status] ?? `Server error (${response.status}).`,
    );
  }
  return data;
}

/** The message to show for a failed query, or null. */
export function errorMessage(error: Error | null): string | null {
  if (!error) return null;
  return error instanceof ApiError ? error.message : "Unexpected error.";
}
