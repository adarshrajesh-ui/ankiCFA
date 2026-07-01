"""Shared score object (contract from docs/prd/INDEX.md).

Every score returned by every model has exactly this shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Score:
    point: Optional[float]
    range: Optional[Tuple[float, float]]
    coverage_pct: float
    confidence: float
    updated_at: str  # ISO-8601 timestamp, injected (deterministic in tests)
    reasons: List[str] = field(default_factory=list)
    abstain: bool = False

    def __post_init__(self) -> None:
        if self.abstain:
            # An abstaining score must NOT report a made-up number.
            if self.point is not None or self.range is not None:
                raise ValueError("abstaining score must have point/range = None")
        else:
            if self.point is None or self.range is None:
                raise ValueError("non-abstaining score requires point and range")
            lo, hi = self.range
            if not (lo <= self.point <= hi):
                raise ValueError(f"point {self.point} not within range {self.range}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be in [0, 1]")
