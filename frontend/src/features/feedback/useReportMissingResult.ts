import { useMutation } from "@tanstack/react-query";
import { type MissingResultReport, api } from "../../api/client";

export async function sendReport(report: MissingResultReport): Promise<void> {
  const { response } = await api.POST("/feedback/missing-result", { body: report });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
}

/**
 * "I did not find my Pokémon": saves the search and what it showed.
 * The reason of a failure is not shown: the trainer can only retry.
 */
export function useReportMissingResult() {
  return useMutation({ mutationFn: sendReport });
}
