import { type ReactNode, useId, useState } from "react";
import type { Matchup, PokemonSuggestion, PokemonType } from "../../api/client";
import { PokemonCard } from "../../shared/PokemonCard";
import { TypeBadge } from "../../shared/TypeBadge";
import { readable } from "../../shared/pokemon";
import { PokemonSearch } from "../suggest/PokemonSearch";
import { THREAT_TITLES, pitfallText, protectionText } from "./labels";
import { useMatchup } from "./useMatchup";

/**
 * "I want to beat this Pokémon": choose it by name, then see its weaknesses and
 * strengths, what it can inflict and what to avoid. Every rule is computed by the API.
 */
export function BattlePrep() {
  const [opponent, setOpponent] = useState<PokemonSuggestion | null>(null);

  return (
    <>
      <PokemonSearch onSelect={setOpponent} />
      {opponent && <MatchupView key={opponent.id} opponent={opponent} />}
    </>
  );
}

function MatchupView({ opponent }: { opponent: PokemonSuggestion }) {
  const { matchup, isLoading, errorMessage } = useMatchup(opponent.id);

  return (
    <div className="flex flex-col gap-4">
      <PokemonCard pokemon={opponent} label={`Opponent: ${opponent.display_name}`} />
      {isLoading ? (
        <p className="text-stone-500">Analyzing the matchup…</p>
      ) : errorMessage ? (
        <p role="alert" className="text-red-700">
          {errorMessage}
        </p>
      ) : (
        matchup && (
          <>
            <TypeSummary matchup={matchup} />
            <Tactics matchup={matchup} />
          </>
        )
      )}
    </div>
  );
}

/** ×0.5 -> "×½": the way multipliers are usually written. */
export function multiplier(value: number): string {
  const fractions: Record<number, string> = { 0.25: "¼", 0.5: "½" };
  return `×${fractions[value] ?? value}`;
}

function TypeSummary({ matchup }: { matchup: Matchup }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <TypeGroup title="Weak against" empty="No weakness.">
        {matchup.weaknesses.map(({ type, multiplier: m }) => (
          <TypeItem key={type} type={type} note={multiplier(m)} />
        ))}
      </TypeGroup>
      <TypeGroup title="Strong against" empty="No type in particular.">
        {matchup.strong_against.map((type) => (
          <TypeItem key={type} type={type} />
        ))}
      </TypeGroup>
      <TypeGroup title="Resists" empty="No resistance.">
        {matchup.resistances.map(({ type, multiplier: m }) => (
          <TypeItem key={type} type={type} note={multiplier(m)} />
        ))}
      </TypeGroup>
      <TypeGroup title="Immune to" empty="No immunity.">
        {matchup.immunities.map(({ type, ability }) => (
          <TypeItem
            key={type}
            type={type}
            // A Pokémon has only one of its abilities: the immunity is possible.
            note={ability ? `if its ability is ${readable(ability)}` : undefined}
          />
        ))}
      </TypeGroup>
    </div>
  );
}

function TypeGroup({
  title,
  empty,
  children,
}: {
  title: string;
  empty: string;
  children: ReactNode[];
}) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="rounded-xl bg-white p-4 shadow-sm">
      <h3 id={id} className="mb-2 font-bold">
        {title}
      </h3>
      {children.length > 0 ? (
        <ul className="flex flex-wrap gap-2">{children}</ul>
      ) : (
        <p className="text-sm text-stone-500">{empty}</p>
      )}
    </section>
  );
}

function TypeItem({ type, note }: { type: PokemonType; note?: string }) {
  return (
    <li className="flex items-center gap-1 text-sm">
      <TypeBadge type={type} />
      {note && <span className="text-stone-600">{note}</span>}
    </li>
  );
}

/** What the opponent can do (beyond its types), avoid or heal, and what not to do to it. */
function Tactics({ matchup }: { matchup: Matchup }) {
  const id = useId();
  const protectionsId = useId();
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <section aria-labelledby={id} className="rounded-xl bg-white p-4 shadow-sm">
        <h3 id={id} className="mb-2 font-bold">
          What it can inflict on you
        </h3>
        {matchup.threats.length > 0 ? (
          <ul className="flex flex-col gap-1 text-sm">
            {matchup.threats.map((threat) => (
              <li key={threat.effect}>
                <span className="font-medium">{THREAT_TITLES[threat.effect]}</span>{" "}
                <span className="text-stone-500">
                  ({threat.sources.map(readable).join(", ")})
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-stone-500">Nothing in particular.</p>
        )}
      </section>
      {matchup.protections.length > 0 && (
        <section
          aria-labelledby={protectionsId}
          className="rounded-xl bg-white p-4 shadow-sm"
        >
          <h3 id={protectionsId} className="mb-2 font-bold">
            What it can avoid or cure
          </h3>
          <ul className="flex flex-col gap-1 text-sm">
            {matchup.protections.map((protection) => (
              <li key={`${protection.kind}-${protection.effect}`}>
                <span className="font-medium">{protectionText(protection)}</span>{" "}
                <span className="text-stone-500">
                  ({protection.sources.map(readable).join(", ")})
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
      {matchup.pitfalls.length > 0 && (
        <section
          aria-label="What to avoid"
          className="rounded-xl border border-amber-300 bg-amber-50 p-4"
        >
          <h3 className="mb-2 font-bold text-amber-900">What to avoid</h3>
          <ul className="flex flex-col gap-1 text-sm text-amber-900">
            {matchup.pitfalls.map((pitfall) => (
              <li key={`${pitfall.kind}-${pitfall.effect}-${pitfall.ability}`}>
                {pitfallText(pitfall)}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
