import type { PokemonDetail } from "../../api/client";
import { pokemonHref } from "../../navigation";
import { readable } from "../../shared/pokemon";

const STATS: { key: keyof Omit<PokemonDetail["stats"], "total">; label: string }[] = [
  { key: "hp", label: "HP" },
  { key: "attack", label: "Attack" },
  { key: "defense", label: "Defense" },
  { key: "special_attack", label: "Sp. Attack" },
  { key: "special_defense", label: "Sp. Defense" },
  { key: "speed", label: "Speed" },
];
/** Highest possible base stat in the games: the bars are relative to it. */
const MAX_STAT = 255;

/** The encyclopedia part of a Pokémon's page. */
export function About({ detail }: { detail: PokemonDetail }) {
  return (
    <div className="flex flex-col gap-5">
      <p>{detail.species.description}</p>

      <dl className="grid grid-cols-3 gap-3 text-center">
        <Fact label="Height" value={`${detail.height_m} m`} />
        <Fact label="Weight" value={`${detail.weight_kg} kg`} />
        <Fact label="Habitat" value={readable(detail.species.habitat)} capitalize />
      </dl>

      <section aria-label="Stats">
        <h4 className="mb-2 font-bold">Stats</h4>
        <table className="w-full text-sm">
          <tbody>
            {STATS.map(({ key, label }) => (
              <tr key={key}>
                <th scope="row" className="w-28 py-0.5 text-left font-normal">
                  {label}
                </th>
                <td className="w-10 text-right font-mono">{detail.stats[key]}</td>
                <td className="pl-3">
                  <div aria-hidden="true" className="h-2 rounded bg-stone-200">
                    <div
                      className="h-2 rounded bg-red-500"
                      style={{ width: `${(detail.stats[key] / MAX_STAT) * 100}%` }}
                    />
                  </div>
                </td>
              </tr>
            ))}
            <tr className="font-bold">
              <th scope="row" className="pt-1 text-left">
                Total
              </th>
              <td className="pt-1 text-right font-mono">{detail.stats.total}</td>
              <td />
            </tr>
          </tbody>
        </table>
      </section>

      {detail.abilities.length > 0 && (
        <section aria-label="Abilities">
          <h4 className="mb-2 font-bold">Abilities</h4>
          <ul className="flex flex-col gap-1 text-sm">
            {detail.abilities.map((ability) => (
              <li key={ability.id}>
                <span className="font-semibold capitalize">
                  {readable(ability.name)}
                </span>{" "}
                <span className="text-stone-600">— {ability.short_effect}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {detail.evolution_family.length > 1 && (
        <section aria-label="Evolution family">
          <h4 className="mb-2 font-bold">Evolution family</h4>
          <ul className="flex flex-wrap gap-2">
            {detail.evolution_family.map((member) => {
              const content = (
                <>
                  <img
                    src={member.sprite}
                    alt=""
                    width={64}
                    height={64}
                    className="h-16 w-16 [image-rendering:pixelated]"
                  />
                  {member.display_name}
                </>
              );
              const shape =
                "flex flex-col items-center rounded-lg border px-3 py-1 text-sm";
              return (
                <li key={member.id}>
                  {member.id === detail.id ? (
                    // The Pokémon on screen is shown in the family, but leads nowhere.
                    <span
                      aria-current="page"
                      className={`${shape} border-red-600 bg-red-50`}
                    >
                      {content}
                    </span>
                  ) : (
                    <a
                      href={pokemonHref(member.name)}
                      className={`${shape} border-stone-200 hover:border-red-500`}
                    >
                      {content}
                    </a>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      )}
    </div>
  );
}

function Fact({
  label,
  value,
  capitalize = false,
}: {
  label: string;
  value: string;
  /** For API slugs ("waters edge"), not for units ("6.5 m"). */
  capitalize?: boolean;
}) {
  return (
    <div className="rounded-lg bg-stone-100 px-2 py-2">
      <dt className="text-xs text-stone-500">{label}</dt>
      <dd className={`font-semibold ${capitalize ? "capitalize" : ""}`}>{value}</dd>
    </div>
  );
}
