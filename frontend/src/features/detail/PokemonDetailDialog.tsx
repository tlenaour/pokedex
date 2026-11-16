import { useEffect, useId, useRef } from "react";
import type { PokemonDetail, PokemonSummary } from "../../api/client";
import { TypeBadge } from "../../shared/TypeBadge";
import { dexNumber, readable } from "../../shared/pokemon";
import { usePokemonDetail } from "./usePokemonDetail";

type Props = {
  /** What the catalog already knows: shown at once, before the details arrive. */
  pokemon: PokemonSummary;
  /** Another Pokémon of the family was chosen. */
  onSelect: (pokemon: PokemonSummary) => void;
  onClose: () => void;
};

/**
 * Detailed card of one Pokémon, opened over the page.
 * The native <dialog> element does the hard parts alone: the rest of the page
 * is inert, Escape closes, and focus goes back to the clicked thumbnail.
 */
export function PokemonDetailDialog({ pokemon, onSelect, onClose }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const { detail, isLoading, errorMessage } = usePokemonDetail(pokemon.id);

  useEffect(() => {
    const dialog = dialogRef.current;
    // No cleanup calling close(): in development React StrictMode runs this
    // effect twice, and that close() would fire the "close" event, which
    // closes the card as soon as it opens. Leaving the page removes the
    // element, which is enough for the browser to end the modal state.
    if (dialog && !dialog.open) dialog.showModal();
  }, []);

  return (
    // The mouse handler only adds "click outside to close"; keyboard users
    // have Escape and the close button.
    // biome-ignore lint/a11y/useKeyWithClickEvents: see above
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      onClose={onClose}
      // A click on the dialog element itself is a click on the backdrop.
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
      className="m-auto w-[calc(100%-2rem)] max-w-2xl rounded-xl border-t-4 border-red-600 bg-white p-0 text-stone-900 shadow-xl backdrop:bg-stone-900/60"
    >
      <div className="flex flex-col gap-5 p-6">
        <div className="flex items-start gap-5">
          <img
            // The large artwork replaces the small sprite once the details are there.
            src={detail?.images.official_artwork ?? pokemon.sprite}
            alt={pokemon.display_name}
            width={160}
            height={160}
            className="h-40 w-40 shrink-0 rounded-xl bg-stone-100 object-contain"
          />
          <div className="min-w-0 flex-1">
            <p className="font-mono text-sm text-stone-400">{dexNumber(pokemon.id)}</p>
            <h3 id={titleId} className="text-2xl font-bold">
              {pokemon.display_name}
            </h3>
            <p className="text-stone-500">{pokemon.genus}</p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {pokemon.types.map((type) => (
                <TypeBadge key={type} type={type} />
              ))}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-lg px-2 text-2xl leading-none text-stone-500 hover:bg-stone-100 hover:text-stone-900"
          >
            ×
          </button>
        </div>

        <div aria-live="polite">
          {errorMessage ? (
            <p className="text-red-700">{errorMessage}</p>
          ) : isLoading ? (
            <p className="text-stone-500">Loading details…</p>
          ) : null}
        </div>

        {detail && <Details detail={detail} current={pokemon} onSelect={onSelect} />}
      </div>
    </dialog>
  );
}

const STATS: { key: keyof Omit<PokemonDetail["stats"], "total">; label: string }[] = [
  { key: "hp", label: "HP" },
  { key: "attack", label: "Attack" },
  { key: "defense", label: "Defense" },
  { key: "special_attack", label: "Sp. Attack" },
  { key: "special_defense", label: "Sp. Defense" },
  { key: "speed", label: "Speed" },
];
/** Highest possible base stat in the games: the bars are relative to it. */
const MAX_STAT = 255;

/** "lightning-rod" -> "lightning rod" (capitalized by CSS). */
function Details({
  detail,
  current,
  onSelect,
}: {
  detail: PokemonDetail;
  current: PokemonSummary;
  onSelect: (pokemon: PokemonSummary) => void;
}) {
  return (
    <>
      <p>{detail.species.description}</p>

      <dl className="grid grid-cols-3 gap-3 text-center">
        <Fact label="Height" value={`${detail.height_m} m`} />
        <Fact label="Weight" value={`${detail.weight_kg} kg`} />
        <Fact label="Habitat" value={readable(detail.species.habitat)} />
      </dl>

      <section aria-label="Stats">
        <h4 className="mb-2 font-bold">Stats</h4>
        <table className="w-full text-sm">
          <tbody>
            {STATS.map(({ key, label }) => (
              <tr key={key}>
                <th scope="row" className="w-28 py-0.5 text-left font-normal">
                  {label}
                </th>
                <td className="w-10 text-right font-mono">{detail.stats[key]}</td>
                <td className="pl-3">
                  <div aria-hidden="true" className="h-2 rounded bg-stone-200">
                    <div
                      className="h-2 rounded bg-red-500"
                      style={{ width: `${(detail.stats[key] / MAX_STAT) * 100}%` }}
                    />
                  </div>
                </td>
              </tr>
            ))}
            <tr className="font-bold">
              <th scope="row" className="pt-1 text-left">
                Total
              </th>
              <td className="pt-1 text-right font-mono">{detail.stats.total}</td>
              <td />
            </tr>
          </tbody>
        </table>
      </section>

      {detail.abilities.length > 0 && (
        <section aria-label="Abilities">
          <h4 className="mb-2 font-bold">Abilities</h4>
          <ul className="flex flex-col gap-1 text-sm">
            {detail.abilities.map((ability) => (
              <li key={ability.id}>
                <span className="font-semibold capitalize">
                  {readable(ability.name)}
                </span>{" "}
                <span className="text-stone-600">— {ability.short_effect}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {detail.evolution_family.length > 1 && (
        <section aria-label="Evolution family">
          <h4 className="mb-2 font-bold">Evolution family</h4>
          <ul className="flex flex-wrap gap-2">
            {detail.evolution_family.map((member) => (
              <li key={member.id}>
                <button
                  type="button"
                  onClick={() => onSelect(member)}
                  // The Pokémon on screen is shown in the family, but leads nowhere.
                  disabled={member.id === current.id}
                  className="flex flex-col items-center rounded-lg border border-stone-200 px-3 py-1 text-sm hover:border-red-500 disabled:border-red-600 disabled:bg-red-50"
                >
                  <img
                    src={member.sprite}
                    alt=""
                    width={64}
                    height={64}
                    className="h-16 w-16 [image-rendering:pixelated]"
                  />
                  {member.display_name}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-stone-100 px-2 py-2">
      <dt className="text-xs text-stone-500">{label}</dt>
      <dd className="font-semibold capitalize">{value}</dd>
    </div>
  );
}
