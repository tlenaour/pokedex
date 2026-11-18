import { useCallback, useEffect, useState } from "react";
import type { PokemonSuggestion } from "../../api/client";
import { pokemonHref } from "../../navigation";

type NameSearch = {
  /** The text the results on screen answer (after the debounce). */
  query: string;
  isLoading: boolean;
  suggestions: PokemonSuggestion[];
};

/**
 * Enter opens the first result of the text in the field. The results on
 * screen may still be those of the previous text (debounce, request in
 * flight): wait for the answer to this text, then open its first result.
 * Typing again (`cancel`) forgets the pending Enter.
 */
export function useOpenFirstResult(search: NameSearch) {
  const [pendingFor, setPendingFor] = useState<string | null>(null);

  useEffect(() => {
    if (pendingFor === null || search.query !== pendingFor || search.isLoading) return;
    setPendingFor(null);
    const first = search.suggestions[0];
    if (first) window.location.hash = pokemonHref(first.name);
  }, [pendingFor, search.query, search.isLoading, search.suggestions]);

  // Stable functions: the home calls `cancel` from an effect.
  const openFirstResultOf = useCallback((text: string) => setPendingFor(text), []);
  const cancel = useCallback(() => setPendingFor(null), []);
  return { openFirstResultOf, cancel };
}
