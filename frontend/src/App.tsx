import { PokemonPage } from "./features/detail/PokemonPage";
import { Home } from "./features/home/Home";
import { HOME_HREF, useRoute } from "./navigation";

export function App() {
  const route = useRoute();

  return (
    <div className="min-h-screen bg-stone-100 text-stone-900">
      <header className="bg-red-600 text-white">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3">
          {/* Pokédex lens: the only decoration. */}
          <span
            aria-hidden="true"
            className="h-8 w-8 shrink-0 rounded-full border-4 border-white bg-sky-400"
          />
          <div>
            <h1 className="text-xl font-bold">
              <a href={HOME_HREF}>Pokédex</a>
            </h1>
            <p className="text-xs text-red-100">
              Find a Pokémon, learn how to beat it.
            </p>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-4">
        {route.page === "pokemon" ? (
          // A new page per Pokémon: nothing of the previous one stays on screen.
          <PokemonPage key={route.name} name={route.name} />
        ) : (
          // No `key` from the URL: the home rewrites its own URL while the
          // visitor types, and remounting would take the focus off the field.
          <Home />
        )}
      </main>
    </div>
  );
}
