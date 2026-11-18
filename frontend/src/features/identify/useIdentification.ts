import { useQuery } from "@tanstack/react-query";
import { api, call, errorMessage } from "../../api/client";
import { isSearchable } from "../../shared/pokemon";

export const IDENTIFY_LIMIT = 10;
/** Same limit as the backend (domain/appearance.py, MAX_DESCRIPTION_LENGTH). */
export const MAX_DESCRIPTION_LENGTH = 300;

/**
 * Pokémon matching a submitted appearance description, best first.
 * Sent on submit only (not while typing): a description is a sentence, not a
 * prefix, and intermediate results would be noise.
 */
export function useIdentification(description: string) {
  const enabled = isSearchable(description);

  const result = useQuery({
    queryKey: ["identify", description],
    queryFn: ({ signal }) =>
      call(
        api.GET("/pokemon/identify", {
          params: { query: { description, limit: IDENTIFY_LIMIT } },
          signal,
        }),
        {
          422: "Invalid description.",
          // The appearance index or the model is missing on the server.
          503: "Search by appearance is unavailable right now.",
        },
      ),
    enabled,
  });

  return {
    results: enabled ? (result.data ?? []) : [],
    isLoading: enabled && result.isFetching,
    isEmpty: enabled && result.isSuccess && result.data.length === 0,
    errorMessage: enabled ? errorMessage(result.error) : null,
  };
}
