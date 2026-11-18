import { QueryClient } from "@tanstack/react-query";

/**
 * The cache of API answers, with the policy shared by every query:
 * - fresh for an hour: the data only changes when the backend re-imports it;
 * - no automatic retry: fail fast and show the message, the next search
 *   starts again normally.
 */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { staleTime: 60 * 60 * 1000, retry: false } },
  });
}
