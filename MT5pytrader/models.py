"""Public outcomes and policies, without terminal side effects."""

from dataclasses import dataclass, field
from typing import Any


class TradeError(RuntimeError):
    """Local validation, connection or query error. No execution is retried."""

    def __init__(self, message, *, code="validation", last_error=None):
        super().__init__(message)
        self.code = code
        self.last_error = last_error


@dataclass(frozen=True)
class TradeResult:
    status: str
    request: dict = field(default_factory=dict)
    retcode: int | None = None
    order: int = 0
    deal: int = 0
    requested_volume: float = 0.0
    executed_volume: float = 0.0
    message: str = ""
    last_error: Any = None
    raw: Any = field(default=None, repr=False, compare=False)

    @property
    def accepted(self):
        return self.status in {"done", "placed", "partial", "unchanged"}

    @property
    def completed(self):
        return self.status in {"done", "unchanged"}


@dataclass(frozen=True)
class CheckResult:
    valid: bool
    request: dict
    retcode: int
    message: str
    raw: Any = field(default=None, repr=False, compare=False)


@dataclass(frozen=True)
class RiskEstimate:
    volume: float
    estimated_loss: float
    margin: float
    currency: str


@dataclass(frozen=True)
class ExecutionLimits:
    allowed_symbols: frozenset[str] | None = None
    max_spread_points: float | None = None
    max_exposure_lots: float | None = None
    max_daily_loss: float | None = None


@dataclass(frozen=True)
class PositionEvent:
    kind: str
    ticket: int
    before: dict | None
    after: dict | None
