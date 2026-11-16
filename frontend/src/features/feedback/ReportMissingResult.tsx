import type { MissingResultReport } from "../../api/client";
import { useReportMissingResult } from "./useReportMissingResult";

/**
 * "Not found?" line under the results of a search. One report per search:
 * render it with `key={query}` so that a new search starts a new report.
 */
export function ReportMissingResult(report: MissingResultReport) {
  const { mutate, isPending, isSuccess, isError } = useReportMissingResult();

  if (isSuccess) {
    return <p className="text-sm text-stone-500">Thanks, noted.</p>;
  }
  return (
    <p className="text-sm text-stone-500">
      {isError ? (
        <span className="text-red-700">Could not send the report. </span>
      ) : (
        "Didn't find your Pokémon? "
      )}
      <button
        type="button"
        disabled={isPending}
        onClick={() => mutate(report)}
        className="font-medium text-red-700 underline hover:text-red-800 disabled:text-stone-400"
      >
        {isError ? "Retry" : "Report"}
      </button>
    </p>
  );
}
