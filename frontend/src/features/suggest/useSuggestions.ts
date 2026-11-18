import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { api, call, errorMessage } from "../../api/client";
import { isSearchable } from "../../shared/pokemon";
import { useDebouncedValue } from "./useDebouncedValue";

export const DEBOUNCE_MS = 200;
export const SUGGESTION_LIMIT = 10;

/**
 * Suggestions for what the trainer is typing.
 *
 * - waits DEBOUNCE_MS after the last keystroke before calling the API;
 * - an outdated request is canceled (TanStack Query passes an AbortSignal);
 * - the previous list stays displayed while the next one loads (no flicker);
 * - results are cached: the data only changes on a backend re-import.
 */
export function useSuggestions(input: string) {
  const query = useDebouncedValue(input.trim(), DEBOUNCE_MS);
  const enabled = isSearchable(query);

  const result = useQuery({
    queryKey: ["suggest", query],
    queryFn: ({ signal }) =>
      call(
        api.GET("/pokemon/suggest", {
          params: { query: { q: query, limit: SUGGESTION_LIMIT } },
          signal,
        }),
        { 422: "Invalid search." },
      ),
    enabled,
    placeholderData: keepPreviousData,
  });

  return {
    /** Debounced query actually sent to the API. */
    query,
    enabled,
    suggestions: enabled ? (result.data ?? []) : [],
    isLoading: enabled && result.isFetching,
    /** True only when the API answered "nothing" for the current query. */
    isEmpty:
      enabled &&
      result.isSuccess &&
      !result.isPlaceholderData &&
      result.data.length === 0,
    /** Message to show, or null. */
    errorMessage: enabled ? errorMessage(result.error) : null,
  };
}
