import { pokemonHref } from "../../navigation";
import type { RecentPokemon } from "./recent";

/** Links back to the last pages shown. Renders nothing when there is none. */
export function RecentlyViewed({ pokemon }: { pokemon: RecentPokemon[] }) {
  if (pokemon.length === 0) return null;
  return (
    <nav aria-label="Recently viewed" className="flex flex-wrap items-center gap-2">
      <span className="text-sm text-stone-500">Recently viewed:</span>
      <ul className="flex flex-wrap gap-2">
        {pokemon.map(({ name, display_name, sprite }) => (
          <li key={name}>
            <a
              href={pokemonHref(name)}
              className="flex min-h-11 items-center gap-1 rounded-full border border-stone-200 bg-white py-1 pr-3 pl-1 text-sm font-medium hover:border-red-500"
            >
              <img
                src={sprite}
                alt=""
                width={32}
                height={32}
                className="h-8 w-8 [image-rendering:pixelated]"
              />
              {display_name}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
