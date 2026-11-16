import type { PokemonSuggestion } from "../../api/client";
import { TypeBadge } from "../../shared/TypeBadge";
import { dexNumber } from "../../shared/pokemon";
import { HighlightedName } from "./HighlightedName";

/** One suggestion: what the trainer needs to recognize the Pokémon they saw. */
export function SuggestionItem({ suggestion }: { suggestion: PokemonSuggestion }) {
  const isFuzzy = suggestion.match.kind === "fuzzy";
  return (
    <div className="flex items-center gap-3">
      {/* Decorative: the name next to it says the same thing. */}
      <img
        src={suggestion.sprite}
        alt=""
        width={64}
        height={64}
        className="h-16 w-16 shrink-0 [image-rendering:pixelated]"
      />
      <div>
        <div className="flex flex-wrap items-baseline gap-x-2">
          <span className="text-lg">
            <HighlightedName segments={suggestion.match.segments} />
          </span>
          <span className="font-mono text-sm text-stone-400">
            {dexNumber(suggestion.id)}
          </span>
          {isFuzzy && (
            <span className="text-sm italic text-stone-500">did you mean?</span>
          )}
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-1.5">
          {suggestion.types.map((type) => (
            <TypeBadge key={type} type={type} />
          ))}
          <span className="text-sm text-stone-500">{suggestion.genus}</span>
        </div>
      </div>
    </div>
  );
}
