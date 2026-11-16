import type { PokemonType } from "../api/client";

// Usual Pokédex type colors. Full class names (not built dynamically) so that
// Tailwind finds and generates them.
const TYPE_COLORS: Record<PokemonType, string> = {
  normal: "bg-stone-400",
  fire: "bg-orange-500",
  water: "bg-blue-500",
  electric: "bg-yellow-400 text-yellow-950",
  grass: "bg-green-500",
  ice: "bg-cyan-400 text-cyan-950",
  fighting: "bg-red-700",
  poison: "bg-purple-500",
  ground: "bg-amber-600",
  flying: "bg-indigo-400",
  psychic: "bg-pink-500",
  bug: "bg-lime-600",
  rock: "bg-yellow-700",
  ghost: "bg-violet-700",
  dragon: "bg-indigo-700",
  dark: "bg-stone-700",
  steel: "bg-slate-500",
  fairy: "bg-pink-300 text-pink-950",
};

export function TypeBadge({ type }: { type: PokemonType }) {
  return (
    <span
      className={`rounded px-2 py-0.5 text-xs font-semibold uppercase text-white ${TYPE_COLORS[type]}`}
    >
      {type}
    </span>
  );
}
