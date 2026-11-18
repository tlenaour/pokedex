import { type ReactNode, useId } from "react";
import type { Matchup, PokemonType } from "../../api/client";
import { TypeBadge } from "../../shared/TypeBadge";
import { readable } from "../../shared/pokemon";
import { THREAT_TITLES, pitfallText, protectionText } from "./labels";

/** ×0.5 -> "×½": the way multipliers are usually written. */
export function multiplier(value: number): string {
  const fractions: Record<number, string> = { 0.25: "¼", 0.5: "½" };
  return `×${fractions[value] ?? value}`;
}

/**
 * What to do against a Pokémon, as three lines of action:
 * - Use and Avoid: what to do, or not, to the opponent ("Immune to sleep"
 *   means "don't try to put it to sleep");
 * - Watch out: what the opponent can do to you.
 * Every fact comes from the API, every sentence from `labels.ts`: no game
 * rule is computed here.
 */
export function HowToBeat({ matchup }: { matchup: Matchup }) {
  const { weaknesses, immunities, resistances, protections, pitfalls } = matchup;
  const { strong_against, threats } = matchup;
  const hasAvoid =
    immunities.length + resistances.length + protections.length + pitfalls.length > 0;
  const hasWatchOut = strong_against.length + threats.length > 0;

  return (
    <div className="flex flex-col divide-y divide-stone-100">
      <Line title="Use">
        {weaknesses.length > 0 ? (
          <TypeList>
            {weaknesses.map(({ type, multiplier: m }) => (
              <TypeItem key={type} type={type} note={multiplier(m)} />
            ))}
          </TypeList>
        ) : (
          <p className="text-sm text-stone-500">No weakness.</p>
        )}
      </Line>

      {hasAvoid && (
        <Line title="Avoid">
          {immunities.length + resistances.length > 0 && (
            <TypeList>
              {immunities.map(({ type, ability }) => (
                <TypeItem
                  key={type}
                  type={type}
                  // A Pokémon has only one of its abilities: the immunity is possible.
                  note={ability ? `×0 if its ability is ${readable(ability)}` : "×0"}
                />
              ))}
              {resistances.map(({ type, multiplier: m }) => (
                <TypeItem key={type} type={type} note={multiplier(m)} />
              ))}
            </TypeList>
          )}
          {protections.length + pitfalls.length > 0 && (
            <ul className="flex flex-col gap-1 text-sm">
              {protections.map((protection) => (
                <li key={`${protection.kind}-${protection.effect}`}>
                  <span className="font-medium">{protectionText(protection)}</span>{" "}
                  <Sources names={protection.sources} />
                </li>
              ))}
              {pitfalls.map((pitfall) => (
                <li
                  key={`${pitfall.kind}-${pitfall.effect}-${pitfall.ability}`}
                  className="text-amber-900"
                >
                  {pitfallText(pitfall)}
                </li>
              ))}
            </ul>
          )}
        </Line>
      )}

      {hasWatchOut && (
        <Line title="Watch out">
          {strong_against.length > 0 && (
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
              <span>Its types hit hard:</span>
              <TypeList>
                {strong_against.map((type) => (
                  <TypeItem key={type} type={type} />
                ))}
              </TypeList>
            </div>
          )}
          {threats.length > 0 && (
            <ul className="flex flex-col gap-1 text-sm">
              {threats.map((threat) => (
                <li key={threat.effect}>
                  <span className="font-medium">{THREAT_TITLES[threat.effect]}</span>{" "}
                  <Sources names={threat.sources} />
                </li>
              ))}
            </ul>
          )}
        </Line>
      )}
    </div>
  );
}

/** One line of action: its title on the left (above, on a phone), then the facts. */
function Line({ title, children }: { title: string; children: ReactNode }) {
  const id = useId();
  return (
    <section
      aria-labelledby={id}
      className="flex flex-col gap-1 py-3 first:pt-0 last:pb-0 sm:flex-row sm:gap-4"
    >
      <h4 id={id} className="shrink-0 font-bold sm:w-24">
        {title}
      </h4>
      <div className="flex min-w-0 flex-col gap-2">{children}</div>
    </section>
  );
}

function TypeList({ children }: { children: ReactNode }) {
  return <ul className="flex flex-wrap gap-x-3 gap-y-1">{children}</ul>;
}

function TypeItem({ type, note }: { type: PokemonType; note?: string }) {
  return (
    <li className="flex items-center gap-1 text-sm">
      <TypeBadge type={type} />
      {note && <span className="text-stone-600">{note}</span>}
    </li>
  );
}

/** The moves or abilities a fact comes from: "(sleep powder, spore)". */
function Sources({ names }: { names: string[] }) {
  return <span className="text-stone-500">({names.map(readable).join(", ")})</span>;
}
