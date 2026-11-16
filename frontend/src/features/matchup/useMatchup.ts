import { useQuery } from "@tanstack/react-query";
import { ApiError, type Matchup, api } from "../../api/client";

export async function fetchMatchup(id: number, signal?: AbortSignal): Promise<Matchup> {
  const { data, response } = await api
    .GET("/pokemon/{ref}/matchup", { params: { path: { ref: String(id) } }, signal })
    .catch((error: unknown) => {
      if (error instanceof Error && error.name === "AbortError") throw error;
      throw new ApiError("API unreachable. Check that the server is running.");
    });
  if (!response.ok || data === undefined) {
    throw new ApiError(`Server error (${response.status}).`);
  }
  return data;
}

/** How to fight one Pokémon. The rules never change: kept in cache. */
export function useMatchup(id: number) {
  const result = useQuery({
    queryKey: ["matchup", id],
    queryFn: ({ signal }) => fetchMatchup(id, signal),
    staleTime: 60 * 60 * 1000,
    retry: false,
  });
  return {
    matchup: result.data,
    isLoading: result.isPending,
    errorMessage: result.error
      ? result.error instanceof ApiError
        ? result.error.message
        : "Unexpected error."
      : null,
  };
}
