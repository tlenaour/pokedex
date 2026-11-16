/**
 * Sentences of the fight preparation, built from the API's codes. The API
 * only sends facts (an effect, an ability...): the wording is the UI's job.
 */
import type { Effect, Pitfall, Protection } from "../../api/client";
import { readable } from "../../shared/pokemon";

/** What the opponent can inflict, as a list title. */
export const THREAT_TITLES: Record<Effect, string> = {
  sleep: "Put to sleep",
  poison: "Poison",
  paralysis: "Paralyze",
  burn: "Burn",
  freeze: "Freeze",
  confusion: "Confuse",
  flinch: "Make flinch",
  infatuation: "Infatuate",
  "one-hit-ko": "Knock out in one hit",
  any: "Inflict a status condition",
};

/** "Immune to poison", "Recovers from poison". */
const EFFECT_NAMES: Record<Effect, string> = {
  sleep: "sleep",
  poison: "poison",
  paralysis: "paralysis",
  burn: "burns",
  freeze: "freezing",
  confusion: "confusion",
  flinch: "flinching",
  infatuation: "infatuation",
  "one-hit-ko": "one-hit KOs",
  any: "status conditions",
};

/** What the opponent can avoid or heal. */
export function protectionText({ kind, effect }: Protection): string {
  const name = EFFECT_NAMES[effect];
  return kind === "cures" ? `Recovers from ${name}` : `Immune to ${name}`;
}

/** "Avoid …" */
const DOING_TO_IT: Record<Effect, string> = {
  sleep: "putting it to sleep",
  poison: "poisoning it",
  paralysis: "paralyzing it",
  burn: "burning it",
  freeze: "freezing it",
  confusion: "confusing it",
  flinch: "making it flinch",
  infatuation: "infatuating it",
  "one-hit-ko": "knocking it out in one hit",
  any: "inflicting a status condition on it",
};

/** What not to do to the opponent. */
export function pitfallText({ kind, effect, ability }: Pitfall): string {
  const why =
    kind === "reflects"
      ? `its ability ${readable(ability)} can pass the status back to you`
      : `its ability ${readable(ability)} makes it stronger`;
  return `Avoid ${DOING_TO_IT[effect]}: ${why}.`;
}
