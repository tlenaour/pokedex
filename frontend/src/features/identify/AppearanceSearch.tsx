import { type FormEvent, useId, useState } from "react";
import type { PokemonSummary } from "../../api/client";
import { PokemonCard } from "../../shared/PokemonCard";
import { TypeBadge } from "../../shared/TypeBadge";
import { dexNumber, isSearchable } from "../../shared/pokemon";
import { PokemonDetailDialog } from "../detail/PokemonDetailDialog";
import { ReportMissingResult } from "../feedback/ReportMissingResult";
import { MAX_DESCRIPTION_LENGTH, useIdentification } from "./useIdentification";

/**
 * Describe what a Pokémon looks like, get the most likely ones.
 * The first result is shown as a card (best guess), the others as a short list.
 */
export function AppearanceSearch() {
  const inputId = useId();
  const [text, setText] = useState("");
  const [submitted, setSubmitted] = useState("");
  const { results, isLoading, isEmpty, errorMessage } = useIdentification(submitted);
  const [best, ...others] = results;
  const [opened, setOpened] = useState<PokemonSummary | null>(null);
  // Report only once the search has answered (results or none), not on errors.
  const canReport = !isLoading && !errorMessage && (results.length > 0 || isEmpty);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitted(text.trim());
  }

  return (
    <div className="flex flex-col gap-4">
      <form onSubmit={onSubmit}>
        <label htmlFor={inputId} className="mb-1 block font-medium">
          Pokémon's appearance
        </label>
        <div className="flex gap-2">
          <input
            id={inputId}
            type="search"
            value={text}
            onChange={(event) => setText(event.target.value)}
            maxLength={MAX_DESCRIPTION_LENGTH}
            placeholder="e.g. small yellow mouse with red cheeks"
            autoComplete="off"
            className="min-w-0 flex-1 rounded-lg border border-stone-300 bg-white px-4 py-3 text-lg shadow-sm outline-none focus:border-red-500 focus:ring-2 focus:ring-red-200"
          />
          <button
            type="submit"
            disabled={!isSearchable(text)}
            className="rounded-lg bg-red-600 px-4 font-semibold text-white shadow-sm hover:bg-red-700 disabled:bg-stone-300"
          >
            Identify
          </button>
        </div>
      </form>

      <p aria-live="polite" className="h-5 text-sm text-stone-500">
        {errorMessage ? (
          <span className="text-red-700">{errorMessage}</span>
        ) : isLoading ? (
          "Identifying…"
        ) : isEmpty ? (
          "No Pokémon found."
        ) : null}
      </p>

      {best && (
        <PokemonCard
          pokemon={best}
          label={`Best match: ${best.display_name}`}
          onOpen={() => setOpened(best)}
        />
      )}
      {others.length > 0 && (
        <section aria-label="Other possibilities">
          <h3 className="mb-2 text-sm font-medium text-stone-500">
            Other possibilities
          </h3>
          <ol className="overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm">
            {others.map((pokemon) => (
              <li
                key={pokemon.id}
                className="relative flex items-center gap-3 border-b border-stone-100 px-3 py-2 last:border-b-0 hover:bg-red-50 has-[:focus-visible]:bg-red-50"
              >
                <img
                  src={pokemon.sprite}
                  alt=""
                  width={48}
                  height={48}
                  className="h-12 w-12 shrink-0 [image-rendering:pixelated]"
                />
                <button
                  type="button"
                  onClick={() => setOpened(pokemon)}
                  aria-haspopup="dialog"
                  className="cursor-pointer font-medium outline-none after:absolute after:inset-0"
                >
                  {pokemon.display_name}
                </button>
                <span className="font-mono text-sm text-stone-400">
                  {dexNumber(pokemon.id)}
                </span>
                <span className="ml-auto flex gap-1.5">
                  {pokemon.types.map((type) => (
                    <TypeBadge key={type} type={type} />
                  ))}
                </span>
              </li>
            ))}
          </ol>
        </section>
      )}
      {opened && (
        <PokemonDetailDialog
          key={opened.id}
          pokemon={opened}
          onSelect={setOpened}
          onClose={() => setOpened(null)}
        />
      )}
      {canReport && (
        <ReportMissingResult
          key={submitted}
          kind="appearance"
          query={submitted}
          shown_ids={results.map((pokemon) => pokemon.id)}
        />
      )}
    </div>
  );
}
