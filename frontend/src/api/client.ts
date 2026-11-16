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
