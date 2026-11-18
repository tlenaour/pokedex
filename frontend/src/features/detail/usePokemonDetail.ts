import { useQuery } from "@tanstack/react-query";
import { api, call, errorMessage } from "../../api/client";

/** Everything about one Pokémon; `ref` is its name or id. */
export function usePokemonDetail(ref: string) {
  const result = useQuery({
    queryKey: ["pokemon", ref],
    queryFn: ({ signal }) =>
      call(api.GET("/pokemon/{ref}", { params: { path: { ref } }, signal })),
  });
  return {
    detail: result.data,
    isLoading: result.isPending,
    errorMessage: errorMessage(result.error),
  };
}
