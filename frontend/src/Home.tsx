import { PAGES, type Page } from "./navigation";

/** One entry per feature, worded as what the visitor wants to do. */
const CHOICES: { page: Page; title: string; description: string }[] = [
  {
    page: "catalog",
    title: "Browse the Pokémon",
    description: "The whole catalog, in Pokédex order.",
  },
  {
    page: "appearance",
    title: "I saw a Pokémon and want to find its name",
    description: "Describe what it looks like: we suggest the closest matches.",
  },
  {
    page: "name",
    title: "I'm not sure of a Pokémon's name",
    description: "Type what you remember, even with a typo.",
  },
  {
    page: "battle",
    title: "I want to beat a Pokémon",
    description: "Its weaknesses, and what it can inflict on you.",
  },
];

/** Landing page: choose a feature. Plain links, so keyboard and Back just work. */
export function Home() {
  return (
    <nav aria-labelledby="home-title" className="flex flex-col gap-6">
      <h2 id="home-title" className="text-xl font-bold">
        What do you want to do?
      </h2>
      <ul className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {CHOICES.map(({ page, title, description }) => (
          <li key={page}>
            <a
              href={PAGES[page]}
              className="flex h-full flex-col gap-2 rounded-xl border border-stone-200 bg-white p-6 shadow-sm outline-none hover:border-red-500 hover:shadow-md focus-visible:border-red-500 focus-visible:ring-2 focus-visible:ring-red-200"
            >
              <span className="text-lg font-bold">{title}</span>
              <span className="text-sm text-stone-500">{description}</span>
              <span aria-hidden="true" className="mt-auto pt-2 font-bold text-red-600">
                →
              </span>
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
