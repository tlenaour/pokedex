import { useQuery } from "@tanstack/react-query";
import { ApiError, type PokemonSummary, api } from "../../api/client";

export async function fetchCatalog(signal?: AbortSignal): Promise<PokemonSummary[]> {
  const { data, response } = await api
    .GET("/pokemon", { signal })
    .catch((error: unknown) => {
      if (error instanceof Error && error.name === "AbortError") throw error;
      throw new ApiError("API unreachable. Check that the server is running.");
    });
  if (!response.ok || data === undefined) {
    throw new ApiError(`Server error (${response.status}).`);
  }
  return data;
}

/**
 * The whole Pokédex, in Pokédex order. No pagination: 151 Pokémon are about
 * 30 KB of JSON, and the pictures only load when they scroll into view.
 */
export function useCatalog() {
  const result = useQuery({
    queryKey: ["catalog"],
    queryFn: ({ signal }) => fetchCatalog(signal),
    staleTime: 60 * 60 * 1000,
    retry: false,
  });
  return {
    pokemon: result.data ?? [],
    isLoading: result.isPending,
    errorMessage: result.error
      ? result.error instanceof ApiError
        ? result.error.message
        : "Unexpected error."
      : null,
  };
}
