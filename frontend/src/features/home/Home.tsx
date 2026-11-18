import { type FormEvent, useEffect, useId, useRef, useState } from "react";
import { type Mode, homeHref, parseRoute } from "../../navigation";
import { rememberHome } from "../../session";
import { isSearchable } from "../../shared/pokemon";
import { useCatalog } from "../catalog/useCatalog";
import { ReportMissingResult } from "../feedback/ReportMissingResult";
import {
  MAX_DESCRIPTION_LENGTH,
  useIdentification,
} from "../identify/useIdentification";
import { RecentlyViewed } from "../recent/RecentlyViewed";
import { readRecent } from "../recent/recent";
import { HighlightedName } from "../suggest/HighlightedName";
import { useSuggestions } from "../suggest/useSuggestions";
import { type GridItem, PokemonGrid } from "./PokemonGrid";
import { useOpenFirstResult } from "./useOpenFirstResult";
import { useScrollRestoration } from "./useScrollRestoration";

const MODES: { mode: Mode; label: string; field: string; placeholder: string }[] = [
  { mode: "name", label: "Name", field: "Pokémon name", placeholder: "e.g. bulba" },
  {
    mode: "description",
    label: "Description",
    field: "Pokémon's appearance",
    placeholder: "e.g. small yellow mouse with red cheeks",
  },
];

/** The search written in the URL, or null when the URL is not the home. */
function searchInUrl() {
  const route = parseRoute(window.location.hash);
  return route.page === "home" ? route : null;
}

/**
 * The home: one search field above the catalog. The results of a search (by
 * name while typing, by description on submit) replace the grid, in the order
 * the API returns them: nothing is filtered or ranked here.
 */
export function Home() {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<Mode>(() => searchInUrl()?.mode ?? "name");
  const [text, setText] = useState(() => searchInUrl()?.q ?? "");
  // Description search: what was last submitted (not what is being typed).
  const [submitted, setSubmitted] = useState(() => {
    const url = searchInUrl();
    return url?.mode === "description" ? url.q : "";
  });
  const [recent] = useState(readRecent);

  const catalog = useCatalog();
  const byName = useSuggestions(mode === "name" ? text : "");
  const byLook = useIdentification(mode === "description" ? submitted : "");
  const enter = useOpenFirstResult(byName);

  const search =
    mode === "name"
      ? {
          kind: "name" as const,
          // `isSearchable(text)`: emptying the field brings the catalog back
          // at once, without waiting for the debounce.
          active: byName.enabled && isSearchable(text),
          query: byName.query,
          items: byName.suggestions.map(
            (suggestion): GridItem => ({
              pokemon: suggestion,
              name: <HighlightedName segments={suggestion.match.segments} />,
              hint: suggestion.match.kind === "fuzzy" ? "did you mean?" : undefined,
            }),
          ),
          isLoading: byName.isLoading,
          isEmpty: byName.isEmpty,
          errorMessage: byName.errorMessage,
        }
      : {
          kind: "appearance" as const,
          active: isSearchable(submitted),
          query: submitted,
          // In a grid, nothing else tells which result is the closest.
          items: byLook.results.map(
            (pokemon, index): GridItem => ({
              pokemon,
              badge: index === 0 ? "Best match" : undefined,
            }),
          ),
          isLoading: byLook.isLoading,
          isEmpty: byLook.isEmpty,
          errorMessage: byLook.errorMessage,
        };

  // The search lives in the URL: Back from a page finds it again, and a link
  // can be shared. `replaceState`: typing never adds a history entry.
  const urlQuery = mode === "name" ? byName.query : submitted;
  useEffect(
    function writeSearchToUrl() {
      // The visitor may already be leaving for a page: don't overwrite its URL.
      if (!searchInUrl()) return;
      const href = homeHref(mode, urlQuery);
      window.history.replaceState(null, "", href);
      rememberHome(href);
    },
    [mode, urlQuery],
  );

  // The URL changed from outside (header link, Back, typed address): follow it.
  // Our own `replaceState` does not fire `hashchange`.
  const cancelEnter = enter.cancel;
  useEffect(
    function followUrl() {
      const follow = () => {
        const url = searchInUrl();
        if (!url) return;
        setMode(url.mode);
        setText(url.q);
        setSubmitted(url.mode === "description" ? url.q : "");
        cancelEnter();
      };
      window.addEventListener("hashchange", follow);
      return () => window.removeEventListener("hashchange", follow);
    },
    [cancelEnter],
  );

  useScrollRestoration(search.active ? !search.isLoading : !catalog.isLoading);

  function changeMode(next: Mode) {
    setMode(next);
    setText("");
    setSubmitted("");
    enter.cancel();
    inputRef.current?.focus();
  }

  function changeText(value: string) {
    setText(value);
    enter.cancel();
    // An emptied field shows the catalog again, in both modes.
    if (value === "") setSubmitted("");
  }

  /** Start over in the same mode: the whole catalog, ready to type again. */
  function clearSearch() {
    changeText("");
    inputRef.current?.focus();
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (mode === "description") setSubmitted(text.trim());
    else enter.openFirstResultOf(text.trim());
  }

  const current = MODES.find((candidate) => candidate.mode === mode) ?? MODES[0];
  const items: GridItem[] = search.active
    ? search.items
    : catalog.pokemon.map((pokemon) => ({ pokemon }));
  const errorMessage = search.active ? search.errorMessage : catalog.errorMessage;
  const isEmpty = search.active && search.isEmpty;
  // Report only once the search has answered (results or none), not on errors.
  const canReport =
    search.active &&
    !search.isLoading &&
    !search.errorMessage &&
    (search.items.length > 0 || search.isEmpty);

  function status(): string | null {
    if (search.active) {
      if (search.isLoading) return "Searching…";
      if (search.isEmpty) return "No Pokémon found.";
      const count = search.items.length;
      return count === 1 ? "1 result" : `${count} results`;
    }
    if (catalog.isLoading) return "Loading the catalog…";
    if (catalog.pokemon.length === 0) return "The Pokédex is empty.";
    return `${catalog.pokemon.length} Pokémon`;
  }

  return (
    <div className="flex flex-col gap-4">
      <h2 className="sr-only">Find a Pokémon</h2>

      <div className="mx-auto flex w-full max-w-2xl flex-col gap-3">
        <fieldset className="flex rounded-lg bg-stone-200 p-1">
          <legend className="sr-only">Search by</legend>
          {MODES.map((option) => (
            <label
              key={option.mode}
              className="flex min-h-11 flex-1 cursor-pointer items-center justify-center rounded-md font-medium text-stone-600 has-[:checked]:bg-white has-[:checked]:text-stone-900 has-[:checked]:shadow-sm has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-red-500"
            >
              <input
                type="radio"
                name="search-mode"
                checked={mode === option.mode}
                onChange={() => changeMode(option.mode)}
                className="sr-only"
              />
              {option.label}
            </label>
          ))}
        </fieldset>

        <form onSubmit={onSubmit}>
          <label htmlFor={inputId} className="sr-only">
            {current.field}
          </label>
          <div className="flex gap-2">
            <div className="relative min-w-0 flex-1">
              <input
                ref={inputRef}
                id={inputId}
                type="search"
                value={text}
                onChange={(event) => changeText(event.target.value)}
                maxLength={mode === "description" ? MAX_DESCRIPTION_LENGTH : undefined}
                placeholder={current.placeholder}
                autoComplete="off"
                spellCheck={mode === "description"}
                // Room on the right for the clear button. The browser's own
                // cross is hidden: not every browser draws one (Firefox), and
                // ours also resets a submitted description search.
                className="w-full rounded-lg border border-stone-300 bg-white py-3 pr-12 pl-4 text-lg shadow-sm outline-none focus:border-red-500 focus:ring-2 focus:ring-red-200 [&::-webkit-search-cancel-button]:appearance-none"
              />
              {text !== "" && (
                <button
                  type="button"
                  onClick={clearSearch}
                  aria-label="Clear search"
                  className="absolute inset-y-0 right-0 flex w-11 items-center justify-center rounded-lg text-2xl leading-none text-stone-500 outline-none hover:text-stone-900 focus-visible:ring-2 focus-visible:ring-red-500"
                >
                  ×
                </button>
              )}
            </div>
            {/* By name the results come while typing: no button to press. */}
            {mode === "description" && (
              <button
                type="submit"
                disabled={!isSearchable(text)}
                className="rounded-lg bg-red-600 px-4 font-semibold text-white shadow-sm hover:bg-red-700 disabled:bg-stone-300"
              >
                Search
              </button>
            )}
          </div>
        </form>

        <RecentlyViewed pokemon={recent} />
      </div>

      {/* Status for sighted users and screen readers (polite: not intrusive).
          Fixed height: the grid does not jump when the text changes. */}
      <p aria-live="polite" className="h-5 text-sm text-stone-500">
        {errorMessage ? <span className="text-red-700">{errorMessage}</span> : status()}
      </p>

      {isEmpty && !errorMessage && mode === "name" && (
        <button
          type="button"
          onClick={() => changeMode("description")}
          className="min-h-11 self-start rounded-lg border border-red-600 px-4 font-semibold text-red-700 hover:bg-red-50"
        >
          Try a description search
        </button>
      )}

      {items.length > 0 && !errorMessage && (
        <PokemonGrid items={items} label={search.active ? "Results" : "Catalog"} />
      )}

      {canReport && (
        <ReportMissingResult
          key={`${search.kind}:${search.query}`}
          kind={search.kind}
          query={search.query}
          shown_ids={search.items.map((item) => item.pokemon.id)}
        />
      )}
    </div>
  );
}
