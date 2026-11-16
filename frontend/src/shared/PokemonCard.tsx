import type { PokemonSummary } from "../api/client";
import { TypeBadge } from "./TypeBadge";
import { dexNumber } from "./pokemon";

type Props = {
  pokemon: PokemonSummary;
  /** Accessible name of the card, e.g. "Best match: Pikachu". */
  label: string;
  /** When given, the card is clickable and opens the detailed card. */
  onOpen?: () => void;
};

/** Big card of one Pokémon: lets the trainer confirm it is the one they had in mind. */
export function PokemonCard({ pokemon, label, onOpen }: Props) {
  return (
    <section
      aria-label={label}
      // `relative`: the button below stretches over the whole card.
      className={`relative flex items-center gap-5 rounded-xl border-t-4 border-red-600 bg-white p-5 shadow-sm ${
        onOpen
          ? "hover:shadow-md hover:ring-2 hover:ring-red-300 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-red-500"
          : ""
      }`}
    >
      <img
        src={pokemon.sprite}
        alt={pokemon.display_name}
        width={128}
        height={128}
        className="h-32 w-32 shrink-0 rounded-full bg-stone-100 [image-rendering:pixelated]"
      />
      <div>
        <p className="font-mono text-sm text-stone-400">{dexNumber(pokemon.id)}</p>
        <h3 className="text-2xl font-bold">
          {onOpen ? (
            // Same pattern as the catalog: the name is the button, its ::after
            // covers the card.
            <button
              type="button"
              onClick={onOpen}
              aria-haspopup="dialog"
              className="cursor-pointer outline-none after:absolute after:inset-0 after:rounded-xl"
            >
              {pokemon.display_name}
            </button>
          ) : (
            pokemon.display_name
          )}
        </h3>
        <p className="text-stone-500">{pokemon.genus}</p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {pokemon.types.map((type) => (
            <TypeBadge key={type} type={type} />
          ))}
        </div>
      </div>
    </section>
  );
}
