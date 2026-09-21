"""MT5 execution helpers. Importing this package never initializes a terminal."""

from .core import Trader
from .models import (
    CheckResult,
    ExecutionLimits,
    PositionEvent,
    RiskEstimate,
    TradeError,
    TradeResult,
)

__version__ = "2.0.0"
__all__ = [
    "Trader",
    "TradeError",
    "TradeResult",
    "CheckResult",
    "RiskEstimate",
    "ExecutionLimits",
    "PositionEvent",
]
