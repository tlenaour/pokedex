import { useQuery } from "@tanstack/react-query";
import { NotFoundError, api, call, errorMessage } from "../../api/client";

/** How to fight one Pokémon; `ref` is its name or id. */
export function useMatchup(ref: string) {
  const result = useQuery({
    queryKey: ["matchup", ref],
    queryFn: ({ signal }) =>
      call(api.GET("/pokemon/{ref}/matchup", { params: { path: { ref } }, signal })),
  });
  return {
    matchup: result.data,
    isLoading: result.isPending,
    isNotFound: result.error instanceof NotFoundError,
    errorMessage: errorMessage(result.error),
  };
}
