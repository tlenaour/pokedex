import { useQuery } from "@tanstack/react-query";
import { ApiError, type PokemonDetail, api } from "../../api/client";

export async function fetchPokemonDetail(
  id: number,
  signal?: AbortSignal,
): Promise<PokemonDetail> {
  const { data, response } = await api
    .GET("/pokemon/{ref}", { params: { path: { ref: String(id) } }, signal })
    .catch((error: unknown) => {
      if (error instanceof Error && error.name === "AbortError") throw error;
      throw new ApiError("API unreachable. Check that the server is running.");
    });
  if (!response.ok || data === undefined) {
    throw new ApiError(`Server error (${response.status}).`);
  }
  return data;
}

/** Everything about one Pokémon. Kept in cache: reopening a card is instant. */
export function usePokemonDetail(id: number) {
  const result = useQuery({
    queryKey: ["pokemon", id],
    queryFn: ({ signal }) => fetchPokemonDetail(id, signal),
    staleTime: 60 * 60 * 1000,
    retry: false,
  });
  return {
    detail: result.data,
    isLoading: result.isPending,
    errorMessage: result.error
      ? result.error instanceof ApiError
        ? result.error.message
        : "Unexpected error."
      : null,
  };
}
