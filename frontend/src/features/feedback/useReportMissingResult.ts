import { useMutation } from "@tanstack/react-query";
import { type MissingResultReport, api, call } from "../../api/client";

/**
 * "I did not find my Pokémon": saves the search and what it showed.
 * Through `call()` like every other request (one error policy). The report
 * line only needs to know that it failed: the trainer can retry.
 */
export function useReportMissingResult() {
  return useMutation({
    mutationFn: (report: MissingResultReport) =>
      call(api.POST("/feedback/missing-result", { body: report })),
  });
}
