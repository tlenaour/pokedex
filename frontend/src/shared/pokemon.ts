/** Pokédex number: 1 -> "#001". */
export const dexNumber = (id: number) => `#${String(id).padStart(3, "0")}`;

/** API slug as text: "lightning-rod" -> "lightning rod". */
export const readable = (slug: string) => slug.replace(/-/g, " ");

// The backend rejects text without any letter or digit (422): don't send it.
const HAS_LETTER_OR_DIGIT = /[\p{L}\p{N}]/u;

export function isSearchable(text: string): boolean {
  return HAS_LETTER_OR_DIGIT.test(text);
}
