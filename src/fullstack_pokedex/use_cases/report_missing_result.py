"""Use case: a trainer reports that a search did not show their Pokémon."""

from dataclasses import dataclass

from fullstack_pokedex.domain.errors import InvalidReportError
from fullstack_pokedex.domain.feedback import MissingResultReport, validate_report
from fullstack_pokedex.domain.repositories import FeedbackRepository, PokemonRepository


@dataclass(frozen=True)
class ReportMissingResult:
    feedback: FeedbackRepository
    pokemon: PokemonRepository

    def execute(self, report: MissingResultReport) -> int:
        """Save the report and return its id."""
        # 1. Validate before writing anything.
        report = validate_report(report)

        # 2. Only save Pokémon that exist: the reports must stay usable.
        if report.shown_ids:
            known = {p.id for p in self.pokemon.get_many(report.shown_ids)}
            if unknown := sorted(set(report.shown_ids) - known):
                raise InvalidReportError(f"unknown Pokémon ids: {unknown}")

        # 3. Save.
        return self.feedback.add(report)
