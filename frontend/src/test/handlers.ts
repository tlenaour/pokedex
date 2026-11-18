import { http, HttpResponse } from "msw";
import type {
  Matchup,
  MissingResultReport,
  NameSegment,
  PokemonDetail,
  PokemonIdentification,
  PokemonSuggestion,
  PokemonSummary,
} from "../api/client";

/** Queries received by the fake API, in order: lets tests count requests. */
export const receivedQueries: string[] = [];

function suggestion(
  id: number,
  name: string,
  displayName: string,
  types: PokemonSuggestion["types"],
  genus: string,
  kind: PokemonSuggestion["match"]["kind"],
  segments: NameSegment[],
): PokemonSuggestion {
  return {
    id,
    name,
    display_name: displayName,
    sprite: `https://example.com/sprites/${id}.png`,
    types,
    genus,
    match: { kind, score: kind === "fuzzy" ? 0.95 : 1, segments },
  };
}

const seg = (text: string, matched: boolean): NameSegment => ({ text, matched });

const BULBASAUR = suggestion(
  1,
  "bulbasaur",
  "Bulbasaur",
  ["grass", "poison"],
  "Seed Pokémon",
  "prefix",
  [seg("Bulba", true), seg("saur", false)],
);

/** Responses of the real backend for these queries (shape checked by TS). */
export const RESPONSES: Record<string, PokemonSuggestion[]> = {
  bulba: [BULBASAUR],
  Bulbasaur: [{ ...BULBASAUR, match: { ...BULBASAUR.match, kind: "exact" } }],
  mime: [
    suggestion(
      122,
      "mr-mime",
      "Mr. Mime",
      ["psychic", "fairy"],
      "Barrier Pokémon",
      "word_prefix",
      [seg("Mr. ", false), seg("Mime", true)],
    ),
  ],
  nido: [
    suggestion(
      29,
      "nidoran-f",
      "Nidoran♀",
      ["poison"],
      "Poison Pin Pokémon",
      "prefix",
      [seg("Nido", true), seg("ran♀", false)],
    ),
    suggestion(30, "nidorina", "Nidorina", ["poison"], "Poison Pin Pokémon", "prefix", [
      seg("Nido", true),
      seg("rina", false),
    ]),
  ],
  bulbsaur: [
    {
      ...BULBASAUR,
      match: { kind: "fuzzy", score: 0.95, segments: [seg("Bulbasaur", false)] },
    },
  ],
};

const identification = (
  id: number,
  displayName: string,
  types: PokemonIdentification["types"],
  genus: string,
  score: number,
): PokemonIdentification => ({
  id,
  name: displayName.toLowerCase(),
  display_name: displayName,
  sprite: `https://example.com/sprites/${id}.png`,
  types,
  genus,
  score,
});

/** Descriptions received by the fake identify route, in order. */
export const receivedDescriptions: string[] = [];

export const IDENTIFICATIONS: Record<string, PokemonIdentification[]> = {
  "small yellow mouse with red cheeks": [
    identification(25, "Pikachu", ["electric"], "Mouse Pokémon", 0.73),
    identification(27, "Sandshrew", ["ground"], "Mouse Pokémon", 0.61),
    identification(100, "Voltorb", ["electric"], "Ball Pokémon", 0.58),
  ],
};

/** The catalog (GET /pokemon), in Pokédex order. */
export const CATALOG: PokemonSummary[] = [
  {
    id: 1,
    name: "bulbasaur",
    display_name: "Bulbasaur",
    types: ["grass", "poison"],
    sprite: "https://example.com/sprites/1.png",
    genus: "Seed Pokémon",
  },
  {
    id: 25,
    name: "pikachu",
    display_name: "Pikachu",
    types: ["electric"],
    sprite: "https://example.com/sprites/25.png",
    genus: "Mouse Pokémon",
  },
  {
    id: 122,
    name: "mr-mime",
    display_name: "Mr. Mime",
    types: ["psychic", "fairy"],
    sprite: "https://example.com/sprites/122.png",
    genus: "Barrier Pokémon",
  },
];

/** The details of Pikachu (GET /pokemon/pikachu), as the real backend answers. */
export const PIKACHU_DETAIL: PokemonDetail = {
  id: 25,
  name: "pikachu",
  display_name: "Pikachu",
  height_m: 0.4,
  weight_kg: 6,
  base_experience: 112,
  types: ["electric"],
  stats: {
    hp: 35,
    attack: 55,
    defense: 40,
    special_attack: 50,
    special_defense: 50,
    speed: 90,
    total: 320,
  },
  species: {
    genus: "Mouse Pokémon",
    description: "When several of these POKéMON gather, their electricity could build.",
    generation: "generation-i",
    color: "yellow",
    shape: "quadruped",
    habitat: "forest",
    is_legendary: false,
    is_mythical: false,
    evolution_chain_id: 10,
  },
  images: {
    sprite: "https://example.com/sprites/25.png",
    official_artwork: "https://example.com/artwork/25.png",
  },
  abilities: [
    { id: 9, name: "static", short_effect: "Has a 30% chance of paralyzing." },
    { id: 31, name: "lightning-rod", short_effect: "Redirects Electric moves." },
  ],
  evolution_family: [
    {
      id: 25,
      name: "pikachu",
      display_name: "Pikachu",
      types: ["electric"],
      sprite: "https://example.com/sprites/25.png",
      genus: "Mouse Pokémon",
    },
    {
      id: 26,
      name: "raichu",
      display_name: "Raichu",
      types: ["electric"],
      sprite: "https://example.com/sprites/26.png",
      genus: "Mouse Pokémon",
    },
  ],
};

/** Raichu only differs by what the tests look at. */
const RAICHU_DETAIL: PokemonDetail = {
  ...PIKACHU_DETAIL,
  id: 26,
  name: "raichu",
  display_name: "Raichu",
  species: {
    ...PIKACHU_DETAIL.species,
    description: "Its long tail serves as a ground.",
  },
};

const DETAILS: Record<string, PokemonDetail> = {
  pikachu: PIKACHU_DETAIL,
  raichu: RAICHU_DETAIL,
};

const summary = (
  id: number,
  name: string,
  displayName: string,
  types: PokemonSummary["types"],
): PokemonSummary => ({
  id,
  name,
  display_name: displayName,
  types,
  sprite: `https://example.com/sprites/${id}.png`,
  genus: "Test Pokémon",
});

/** Bulbasaur: Grass/Poison. */
export const BULBASAUR_MATCHUP: Matchup = {
  pokemon: summary(1, "bulbasaur", "Bulbasaur", ["grass", "poison"]),
  weaknesses: [
    { type: "fire", multiplier: 2 },
    { type: "ice", multiplier: 2 },
    { type: "flying", multiplier: 2 },
    { type: "psychic", multiplier: 2 },
  ],
  resistances: [
    { type: "grass", multiplier: 0.25 },
    { type: "water", multiplier: 0.5 },
  ],
  immunities: [],
  strong_against: ["water", "grass", "ground", "rock", "fairy"],
  threats: [
    { effect: "sleep", sources: ["sleep-powder"] },
    { effect: "poison", sources: ["poison-powder"] },
  ],
  protections: [],
  pitfalls: [],
};

/** Mr. Mime: no weakness, an immunity given by its types and a possible one. */
const MR_MIME_MATCHUP: Matchup = {
  ...BULBASAUR_MATCHUP,
  pokemon: summary(122, "mr-mime", "Mr. Mime", ["psychic", "fairy"]),
  weaknesses: [],
  immunities: [
    { type: "dragon", ability: null },
    { type: "ground", ability: "levitate" },
  ],
  threats: [],
  protections: [
    { kind: "prevents", effect: "sleep", sources: ["insomnia"] },
    { kind: "cures", effect: "any", sources: ["natural-cure", "shed-skin"] },
  ],
  pitfalls: [
    { kind: "reflects", effect: "poison", ability: "synchronize" },
    { kind: "boosts", effect: "any", ability: "guts" },
  ],
};

/** Pikachu and Raichu: a weakness and nothing else to say. */
const plainMatchup = (pokemon: PokemonSummary): Matchup => ({
  pokemon,
  weaknesses: [{ type: "ground", multiplier: 2 }],
  resistances: [],
  immunities: [],
  strong_against: [],
  threats: [],
  protections: [],
  pitfalls: [],
});

const MATCHUPS: Record<string, Matchup> = {
  bulbasaur: BULBASAUR_MATCHUP,
  "mr-mime": MR_MIME_MATCHUP,
  pikachu: plainMatchup(summary(25, "pikachu", "Pikachu", ["electric"])),
  raichu: plainMatchup(summary(26, "raichu", "Raichu", ["electric"])),
};

/** Reports received by the fake feedback route, in order. */
export const receivedReports: MissingResultReport[] = [];

export const handlers = [
  http.get("*/api/pokemon", () => HttpResponse.json(CATALOG)),
  http.post("*/api/feedback/missing-result", async ({ request }) => {
    receivedReports.push((await request.json()) as MissingResultReport);
    return HttpResponse.json({ id: receivedReports.length }, { status: 201 });
  }),
  http.get("*/api/pokemon/identify", ({ request }) => {
    const description = new URL(request.url).searchParams.get("description") ?? "";
    receivedDescriptions.push(description);
    return HttpResponse.json(IDENTIFICATIONS[description] ?? []);
  }),
  http.get("*/api/pokemon/suggest", ({ request }) => {
    const q = new URL(request.url).searchParams.get("q") ?? "";
    receivedQueries.push(q);
    return HttpResponse.json(RESPONSES[q] ?? []);
  }),
  http.get("*/api/pokemon/:ref/matchup", ({ params }) => {
    const matchup = MATCHUPS[String(params.ref)];
    return matchup
      ? HttpResponse.json(matchup)
      : HttpResponse.json({ detail: "Pokemon not found" }, { status: 404 });
  }),
  // Last: `:ref` would otherwise capture "identify" and "suggest".
  http.get("*/api/pokemon/:ref", ({ params }) => {
    const detail = DETAILS[String(params.ref)];
    return detail
      ? HttpResponse.json(detail)
      : HttpResponse.json({ detail: "Pokemon not found" }, { status: 404 });
  }),
];
