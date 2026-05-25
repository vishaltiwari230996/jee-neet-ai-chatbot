"""Injectable clock.

`datetime.now()` is one of the worst sources of flaky tests. Every domain
function that needs "now" takes a `Clock` from the container. Production
binds it to a UTC clock; tests bind a fixed-time fake.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime: ...
