import { useQuery } from "@tanstack/react-query";
import { api, call, errorMessage } from "../../api/client";

/**
 * The whole Pokédex, in Pokédex order. No pagination: 151 Pokémon are about
 * 30 KB of JSON, and the pictures only load when they scroll into view.
 */
export function useCatalog() {
  const result = useQuery({
    queryKey: ["catalog"],
    queryFn: ({ signal }) => call(api.GET("/pokemon", { signal })),
  });
  return {
    pokemon: result.data ?? [],
    isLoading: result.isPending,
    errorMessage: errorMessage(result.error),
  };
}
