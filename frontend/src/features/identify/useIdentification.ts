import { useQuery } from "@tanstack/react-query";
import { ApiError, type PokemonIdentification, api } from "../../api/client";
import { isSearchable } from "../../shared/pokemon";

export const IDENTIFY_LIMIT = 5;
/** Same limit as the backend (domain/appearance.py, MAX_DESCRIPTION_LENGTH). */
export const MAX_DESCRIPTION_LENGTH = 300;

export async function fetchIdentification(
  description: string,
  signal?: AbortSignal,
): Promise<PokemonIdentification[]> {
  const { data, response } = await api
    .GET("/pokemon/identify", {
      params: { query: { description, limit: IDENTIFY_LIMIT } },
      signal,
    })
    .catch((error: unknown) => {
      if (error instanceof Error && error.name === "AbortError") throw error;
      throw new ApiError("API unreachable. Check that the server is running.");
    });

  if (!response.ok || data === undefined) {
    const messages: Record<number, string> = {
      422: "Invalid description.",
      // The appearance index is missing or outdated on the server.
      503: "Search by appearance is unavailable right now.",
    };
    throw new ApiError(
      messages[response.status] ?? `Server error (${response.status}).`,
    );
  }
  return data;
}

/**
 * Pokémon matching a submitted appearance description, best first.
 * Sent on submit only (not while typing): a description is a sentence, not a
 * prefix, and intermediate results would be noise.
 */
export function useIdentification(description: string) {
  const enabled = isSearchable(description);

  const result = useQuery({
    queryKey: ["identify", description],
    queryFn: ({ signal }) => fetchIdentification(description, signal),
    enabled,
    staleTime: 60 * 60 * 1000,
    retry: false,
  });

  return {
    results: enabled ? (result.data ?? []) : [],
    isLoading: enabled && result.isFetching,
    isEmpty: enabled && result.isSuccess && result.data.length === 0,
    errorMessage:
      enabled && result.error
        ? result.error instanceof ApiError
          ? result.error.message
          : "Unexpected error."
        : null,
  };
}
