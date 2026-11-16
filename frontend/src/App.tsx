import { type ReactNode, useState } from "react";
import { Home } from "./Home";
import type { PokemonSummary } from "./api/client";
import { PokemonCatalog } from "./features/catalog/PokemonCatalog";
import { PokemonDetailDialog } from "./features/detail/PokemonDetailDialog";
import { AppearanceSearch } from "./features/identify/AppearanceSearch";
import { BattlePrep } from "./features/matchup/BattlePrep";
import { PokemonSearch } from "./features/suggest/PokemonSearch";
import { PAGES, usePage } from "./navigation";

export function App() {
  const page = usePage();

  return (
    <div className="min-h-screen bg-stone-100 text-stone-900">
      <header className="bg-red-600 text-white">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-5">
          {/* Pokédex lens: the only decoration. */}
          <span
            aria-hidden="true"
            className="h-9 w-9 shrink-0 rounded-full border-4 border-white bg-sky-400"
          />
          <div>
            <h1 className="text-2xl font-bold">
              <a href={PAGES.home}>Pokédex</a>
            </h1>
            <p className="text-sm text-red-100">
              Browse the catalog, find a Pokémon by its name or appearance, or prepare a
              battle.
            </p>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        {page === "home" && <Home />}
        {page === "catalog" && (
          <FeaturePage id="catalog" title="Catalog">
            <PokemonCatalog />
          </FeaturePage>
        )}
        {page === "appearance" && (
          <FeaturePage id="by-appearance" title="By appearance" narrow>
            <AppearanceSearch />
          </FeaturePage>
        )}
        {page === "battle" && (
          <FeaturePage id="battle" title="Prepare a battle" narrow>
            <BattlePrep />
          </FeaturePage>
        )}
        {page === "name" && (
          <FeaturePage id="by-name" title="By name" narrow>
            <NameSearch />
          </FeaturePage>
        )}
      </main>
    </div>
  );
}

type FeaturePageProps = {
  id: string;
  title: string;
  /** Search pages read better in a narrow column; the catalog uses the full width. */
  narrow?: boolean;
  children: ReactNode;
};

/** A feature on its own page, with the way back to the choice. */
function FeaturePage({ id, title, narrow = false, children }: FeaturePageProps) {
  return (
    <div className={`flex flex-col gap-6 ${narrow ? "mx-auto max-w-2xl" : ""}`}>
      <a href={PAGES.home} className="self-start text-sm text-red-700 hover:underline">
        ← Change search
      </a>
      <section aria-labelledby={id} className="flex flex-col gap-4">
        <h2 id={id} className="text-xl font-bold">
          {title}
        </h2>
        {children}
      </section>
    </div>
  );
}

/** Choosing a suggestion opens the detailed card at once: the suggestion
 * already shows what is needed to recognize the Pokémon. */
function NameSearch() {
  const [opened, setOpened] = useState<PokemonSummary | null>(null);

  return (
    <>
      <PokemonSearch onSelect={setOpened} keepSearch />
      {opened && (
        <PokemonDetailDialog
          key={opened.id}
          pokemon={opened}
          onSelect={setOpened}
          onClose={() => setOpened(null)}
        />
      )}
    </>
  );
}
