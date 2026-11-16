import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ApiError, type PokemonSuggestion, api } from "../../api/client";
import { isSearchable } from "../../shared/pokemon";
import { useDebouncedValue } from "./useDebouncedValue";

export const DEBOUNCE_MS = 200;
export const SUGGESTION_LIMIT = 5;

export async function fetchSuggestions(
  q: string,
  signal?: AbortSignal,
): Promise<PokemonSuggestion[]> {
  const { data, response } = await api
    .GET("/pokemon/suggest", {
      params: { query: { q, limit: SUGGESTION_LIMIT } },
      signal,
    })
    .catch((error: unknown) => {
      // A cancelled request (outdated query) is not an error to show.
      if (error instanceof Error && error.name === "AbortError") throw error;
      throw new ApiError("API unreachable. Check that the server is running.");
    });

  if (!response.ok || data === undefined) {
    throw new ApiError(
      response.status === 422
        ? "Invalid search."
        : `Server error (${response.status}).`,
    );
  }
  return data;
}

/**
 * Suggestions for what the trainer is typing.
 *
 * - waits DEBOUNCE_MS after the last keystroke before calling the API;
 * - an outdated request is cancelled (TanStack Query passes an AbortSignal);
 * - the previous list stays displayed while the next one loads (no flicker);
 * - results are cached: the data only changes on a backend re-import.
 */
export function useSuggestions(input: string) {
  const query = useDebouncedValue(input.trim(), DEBOUNCE_MS);
  const enabled = isSearchable(query);

  const result = useQuery({
    queryKey: ["suggest", query],
    queryFn: ({ signal }) => fetchSuggestions(query, signal),
    enabled,
    placeholderData: keepPreviousData,
    staleTime: 60 * 60 * 1000,
    retry: false,
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
    errorMessage:
      enabled && result.error
        ? result.error instanceof ApiError
          ? result.error.message
          : "Unexpected error."
        : null,
  };
}
