import { useState } from "react";
import type { PokemonSummary } from "../../api/client";
import { TypeBadge } from "../../shared/TypeBadge";
import { dexNumber } from "../../shared/pokemon";
import { PokemonDetailDialog } from "../detail/PokemonDetailDialog";
import { useCatalog } from "./useCatalog";

/**
 * The Pokédex as a product catalog: a grid, up to 5 Pokémon per row.
 * Clicking a Pokémon opens its detailed card over the grid.
 */
export function PokemonCatalog() {
  const { pokemon, isLoading, errorMessage } = useCatalog();
  const [opened, setOpened] = useState<PokemonSummary | null>(null);

  if (isLoading) return <p className="text-stone-500">Loading the catalog…</p>;
  if (errorMessage) return <p className="text-red-700">{errorMessage}</p>;
  if (pokemon.length === 0)
    return <p className="text-stone-500">The Pokédex is empty.</p>;

  return (
    <>
      <p className="text-sm text-stone-500">{pokemon.length} Pokémon</p>
      {/* Responsive grid: the number of columns follows the screen width. */}
      <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
        {pokemon.map((p) => (
          <li key={p.id}>
            <CatalogItem pokemon={p} onOpen={() => setOpened(p)} />
          </li>
        ))}
      </ul>
      {opened && (
        <PokemonDetailDialog
          // A new dialog per Pokémon: nothing of the previous one stays on screen.
          key={opened.id}
          pokemon={opened}
          onSelect={setOpened}
          onClose={() => setOpened(null)}
        />
      )}
    </>
  );
}

function CatalogItem({
  pokemon,
  onOpen,
}: {
  pokemon: PokemonSummary;
  onOpen: () => void;
}) {
  return (
    <article
      aria-label={pokemon.display_name}
      // `relative`: the button below stretches over the whole thumbnail.
      className="relative flex h-full flex-col items-center rounded-xl bg-white p-3 text-center shadow-sm hover:shadow-md hover:ring-2 hover:ring-red-300 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-red-500"
    >
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
        {/* The name is the button; its ::after covers the thumbnail, so the
            whole thumbnail is clickable while screen readers hear one name. */}
        <button
          type="button"
          onClick={onOpen}
          aria-haspopup="dialog"
          className="cursor-pointer outline-none after:absolute after:inset-0 after:rounded-xl"
        >
          {pokemon.display_name}
        </button>
      </h3>
      <p className="mb-2 text-xs text-stone-500">{pokemon.genus}</p>
      <div className="mt-auto flex flex-wrap justify-center gap-1">
        {pokemon.types.map((type) => (
          <TypeBadge key={type} type={type} />
        ))}
      </div>
    </article>
  );
}
