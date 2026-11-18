import type { ReactNode } from "react";
import type { PokemonSummary } from "../../api/client";
import { pokemonHref } from "../../navigation";
import { TypeBadge } from "../../shared/TypeBadge";
import { dexNumber } from "../../shared/pokemon";

export type GridItem = {
  pokemon: PokemonSummary;
  /** The name as the search wants it shown (matching part in bold). */
  name?: ReactNode;
  /** Label over the card, e.g. "Best match". */
  badge?: string;
  /** Remark next to the name, e.g. "did you mean?". */
  hint?: string;
};

/**
 * The catalog and the results of both searches: one grid, the same cards.
 * Responsive: the number of columns follows the screen width (2 on a phone,
 * up to 5).
 */
export function PokemonGrid({ items, label }: { items: GridItem[]; label: string }) {
  return (
    <ul
      aria-label={label}
      className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5"
    >
      {items.map((item) => (
        <li key={item.pokemon.id}>
          <PokemonGridCard {...item} />
        </li>
      ))}
    </ul>
  );
}

function PokemonGridCard({ pokemon, name, badge, hint }: GridItem) {
  return (
    <article
      aria-label={pokemon.display_name}
      // `relative`: the link below stretches over the whole card.
      className="relative flex h-full flex-col items-center rounded-xl bg-white p-3 text-center shadow-sm hover:shadow-md hover:ring-2 hover:ring-red-300 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-red-500"
    >
      {badge && (
        <p className="absolute top-2 left-2 rounded bg-red-600 px-1.5 py-0.5 text-xs font-semibold text-white">
          {badge}
        </p>
      )}
      <img
        src={pokemon.sprite}
        alt=""
        width={96}
        height={96}
        // Native lazy loading: only the pictures on screen are downloaded.
        loading="lazy"
        className="h-24 w-24 [image-rendering:pixelated]"
      />
      <p className="font-mono text-xs text-stone-400">{dexNumber(pokemon.id)}</p>
      <h3 className="font-bold">
        {/* The name is the link; its ::after covers the card, so the whole
            card is clickable while screen readers hear one name. That name is
            given explicitly: the bold part of a result must not cut it in two. */}
        <a
          href={pokemonHref(pokemon.name)}
          aria-label={pokemon.display_name}
          className="outline-none after:absolute after:inset-0 after:rounded-xl"
        >
          {name ?? pokemon.display_name}
        </a>
      </h3>
      {hint && <p className="text-xs text-stone-500 italic">{hint}</p>}
      <p className="mb-2 text-xs text-stone-500">{pokemon.genus}</p>
      <div className="mt-auto flex flex-wrap justify-center gap-1">
        {pokemon.types.map((type) => (
          <TypeBadge key={type} type={type} />
        ))}
      </div>
    </article>
  );
}
