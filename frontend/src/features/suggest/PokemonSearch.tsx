import { useCombobox } from "downshift";
import { useId, useState } from "react";
import type { PokemonSuggestion } from "../../api/client";
import { useReportMissingResult } from "../feedback/useReportMissingResult";
import { SuggestionItem } from "./SuggestionItem";
import { useSuggestions } from "./useSuggestions";

type Props = {
  onSelect: (pokemon: PokemonSuggestion) => void;
  /**
   * Keep the typed text and the list after a choice, instead of replacing the
   * text with the chosen name: for when the choice opens something to come
   * back from (the detailed card).
   */
  keepSearch?: boolean;
};

/** Last line of the list: "I did not find my Pokémon". */
const REPORT_ITEM = { report: true } as const;
type Item = PokemonSuggestion | typeof REPORT_ITEM;
const isReport = (item: Item | null): item is typeof REPORT_ITEM =>
  item === REPORT_ITEM;

/**
 * Autocomplete field. Downshift handles the combobox behaviour (keyboard,
 * ARIA attributes for screen readers); we write the markup and the styles.
 * The list is exactly what the API returns, already ranked: no client filtering.
 * A last line lets the trainer report that their Pokémon is not in it.
 */
export function PokemonSearch({ onSelect, keepSearch = false }: Props) {
  const inputId = useId();
  const [inputValue, setInputValue] = useState("");
  const { query, suggestions, enabled, isLoading, isEmpty, errorMessage } =
    useSuggestions(inputValue);
  const report = useReportMissingResult();
  // One report per search: the state only applies to the query it was sent for.
  const reportFor = report.variables?.query === query ? report : null;

  // The report line appears once the API has answered for the current query,
  // so that the report carries the list actually on screen.
  const canReport = enabled && !isLoading && !errorMessage;
  const items: Item[] =
    canReport && (suggestions.length > 0 || isEmpty)
      ? [...suggestions, REPORT_ITEM]
      : [];

  const {
    isOpen,
    highlightedIndex,
    getLabelProps,
    getInputProps,
    getMenuProps,
    getItemProps,
  } = useCombobox<Item>({
    items,
    inputId,
    inputValue,
    // Never kept: choosing the same Pokémon again is a new change, so its
    // card can be reopened after being closed.
    selectedItem: null,
    itemToString: (item) => (item && !isReport(item) ? item.display_name : ""),
    onInputValueChange: ({ inputValue: value }) => setInputValue(value ?? ""),
    stateReducer: (state, { type, changes }) => {
      // No selection is kept (see above), so there is no text to sync with it:
      // without this, Downshift empties the field after a choice.
      if (type === useCombobox.stateChangeTypes.ControlledPropUpdatedSelectedItem)
        return state;
      const kept = {
        ...changes,
        inputValue: state.inputValue,
        isOpen: true,
        highlightedIndex: state.highlightedIndex,
      };
      // Choosing the report line keeps the typed text and the list open.
      if (isReport(changes.selectedItem ?? null)) return kept;
      if (!keepSearch) return changes;
      // So does choosing a Pokémon here. The card it opens takes the focus:
      // leaving the field must then neither close the list nor choose again.
      if (type === useCombobox.stateChangeTypes.InputBlur) return state;
      return changes.selectedItem ? kept : changes;
    },
    onSelectedItemChange: ({ selectedItem: item }) => {
      if (!item) return;
      if (isReport(item)) {
        if (!reportFor?.isPending && !reportFor?.isSuccess) {
          report.mutate({
            kind: "name",
            query,
            shown_ids: suggestions.map((suggestion) => suggestion.id),
          });
        }
        return;
      }
      onSelect(item);
    },
  });

  const showMenu = isOpen && items.length > 0;

  return (
    <div>
      <label {...getLabelProps()} htmlFor={inputId} className="mb-1 block font-medium">
        Pokémon name
      </label>
      <input
        {...getInputProps()}
        placeholder="e.g. bulba"
        autoComplete="off"
        spellCheck={false}
        className="w-full rounded-lg border border-stone-300 bg-white px-4 py-3 text-lg shadow-sm outline-none focus:border-red-500 focus:ring-2 focus:ring-red-200"
      />

      {/* Status for sighted users and screen readers (polite: not intrusive). */}
      <p aria-live="polite" className="mt-1 h-5 text-sm text-stone-500">
        {errorMessage ? (
          <span className="text-red-700">{errorMessage}</span>
        ) : isLoading ? (
          "Searching…"
        ) : isEmpty ? (
          "No Pokémon found."
        ) : null}
      </p>

      {/* Downshift needs the menu element in the DOM even when closed. */}
      <ul
        {...getMenuProps()}
        className={`mt-1 overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm ${
          showMenu ? "" : "hidden"
        }`}
      >
        {showMenu &&
          items.map((item, index) => (
            <li
              key={isReport(item) ? "report" : item.id}
              {...getItemProps({ item, index })}
              className={`cursor-pointer border-b border-stone-100 px-3 py-2 last:border-b-0 ${
                highlightedIndex === index ? "bg-red-50" : ""
              }`}
            >
              {isReport(item) ? (
                <span className="text-sm text-stone-600">
                  {reportFor?.isSuccess
                    ? "Thanks, noted."
                    : reportFor?.isPending
                      ? "Sending…"
                      : reportFor?.isError
                        ? "Could not send the report. Retry"
                        : "I didn't find my Pokémon"}
                </span>
              ) : (
                <SuggestionItem suggestion={item} />
              )}
            </li>
          ))}
      </ul>
    </div>
  );
}
