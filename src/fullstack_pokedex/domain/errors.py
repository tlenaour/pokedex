class DomainError(Exception):
    """Base class for business errors."""


class NotFoundError(DomainError):
    def __init__(self, entity: str, ref: int | str) -> None:
        super().__init__(f"{entity} '{ref}' not found")
        self.entity = entity
        self.ref = ref


class InvalidSearchQueryError(DomainError):
    def __init__(self, query: str, reason: str) -> None:
        super().__init__(f"Invalid search query '{query}': {reason}")
        self.query = query
        self.reason = reason


class InvalidReportError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid report: {reason}")
        self.reason = reason
