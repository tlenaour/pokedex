import { type ReactNode, useEffect, useId } from "react";
import type { PokemonSummary } from "../../api/client";
import { parseRoute } from "../../navigation";
import { lastHomeHref } from "../../session";
import { TypeBadge } from "../../shared/TypeBadge";
import { dexNumber } from "../../shared/pokemon";
import { HowToBeat } from "../matchup/HowToBeat";
import { useMatchup } from "../matchup/useMatchup";
import { addRecent } from "../recent/recent";
import { About } from "./About";
import { usePokemonDetail } from "./usePokemonDetail";

/**
 * The page of one Pokémon: how to beat it first (what a player in a fight
 * came for), the encyclopedia below.
 * Two requests in parallel: neither part waits for the other, and each one
 * still shows when the other fails.
 */
export function PokemonPage({ name }: { name: string }) {
  const matchup = useMatchup(name);
  const detail = usePokemonDetail(name);

  // Hash navigation keeps the scroll position: without this, a card clicked
  // at the bottom of the grid would open its page in the middle.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  const shown = matchup.matchup?.pokemon;
  useEffect(() => {
    if (shown) addRecent(shown);
  }, [shown]);

  if (matchup.isNotFound || (matchup.errorMessage && detail.errorMessage)) {
    return (
      <Layout>
        <p role="alert" className="text-red-700">
          {matchup.errorMessage}
        </p>
      </Layout>
    );
  }

  // The matchup carries the header; if it failed, the details give the same
  // facts under other field names.
  const fromDetail: PokemonSummary | null = detail.detail
    ? {
        id: detail.detail.id,
        name: detail.detail.name,
        display_name: detail.detail.display_name,
        genus: detail.detail.species.genus,
        types: detail.detail.types,
        sprite: detail.detail.images.sprite,
      }
    : null;
  const pokemon = shown ?? fromDetail;

  return (
    <Layout>
      {pokemon && (
        <header className="flex items-center gap-4">
          <img
            // The large artwork replaces the small sprite once the details are
            // there. Fixed size from the start: nothing moves when it does.
            src={detail.detail?.images.official_artwork ?? pokemon.sprite}
            alt=""
            width={96}
            height={96}
            className="h-24 w-24 shrink-0 rounded-xl bg-white object-contain md:h-32 md:w-32"
          />
          <div className="min-w-0">
            <p className="font-mono text-sm text-stone-400">{dexNumber(pokemon.id)}</p>
            <h2 className="text-2xl font-bold">{pokemon.display_name}</h2>
            <p className="text-sm text-stone-500">{pokemon.genus}</p>
            <div className="mt-1 flex flex-wrap gap-1.5">
              {pokemon.types.map((type) => (
                <TypeBadge key={type} type={type} />
              ))}
            </div>
          </div>
        </header>
      )}

      <Block title="How to beat it" accent>
        {matchup.matchup ? (
          <HowToBeat matchup={matchup.matchup} />
        ) : (
          <Pending isLoading={matchup.isLoading} errorMessage={matchup.errorMessage} />
        )}
      </Block>

      <Block title="About">
        {detail.detail ? (
          <About detail={detail.detail} />
        ) : (
          <Pending isLoading={detail.isLoading} errorMessage={detail.errorMessage} />
        )}
      </Block>
    </Layout>
  );
}

function Layout({ children }: { children: ReactNode }) {
  // Back where the visitor came from: the search and its mode, like the
  // browser's Back button. The header's "Pokédex" link is the way to start over.
  const home = lastHomeHref();
  const route = parseRoute(home);
  const hasSearch = route.page === "home" && route.q !== "";
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-3">
      <a
        href={home}
        className="flex min-h-11 items-center self-start text-sm text-red-700 hover:underline"
      >
        {hasSearch ? "← Back to results" : "← All Pokémon"}
      </a>
      {children}
    </div>
  );
}

function Block({
  title,
  accent = false,
  children,
}: {
  title: string;
  accent?: boolean;
  children: ReactNode;
}) {
  const id = useId();
  return (
    <section
      aria-labelledby={id}
      className={`rounded-xl bg-white p-4 shadow-sm ${accent ? "border-t-4 border-red-600" : ""}`}
    >
      <h3
        id={id}
        className="mb-3 text-xs font-bold tracking-wide text-stone-500 uppercase"
      >
        {title}
      </h3>
      {children}
    </section>
  );
}

/** What stands for a part of the page that is not there (yet). */
function Pending({
  isLoading,
  errorMessage,
}: {
  isLoading: boolean;
  errorMessage: string | null;
}) {
  return (
    <p aria-live="polite" className={errorMessage ? "text-red-700" : "text-stone-500"}>
      {errorMessage ?? (isLoading ? "Loading…" : null)}
    </p>
  );
}
