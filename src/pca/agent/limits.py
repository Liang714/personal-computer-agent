"""Hard limits and cancellation (spec §10).

Enforced by the broker. A plan can never raise its own ceiling.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from pydantic import BaseModel, ConfigDict

from pca.core.errors import BudgetExhausted


class Budget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_actions: int = 25
    max_seconds: float = 300.0
    max_retries: int = 2
    max_model_calls: int = 20


class BudgetTracker:
    def __init__(self, budget: Budget, clock: Callable[[], float] = time.monotonic) -> None:
        self._budget = budget
        self._clock = clock
        self._started = clock()
        self._actions = 0
        self._model_calls = 0
        self._retries = 0
        self._cancelled = False

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    @property
    def consumed(self) -> dict[str, int]:
        return {
            "actions": self._actions,
            "model_calls": self._model_calls,
            "retries": self._retries,
        }

    def cancel(self) -> None:
        self._cancelled = True

    def charge_action(self) -> None:
        self._actions += 1
        if self._actions > self._budget.max_actions:
            raise BudgetExhausted(
                f"max_actions exceeded ({self._budget.max_actions}); consumed {self.consumed}"
            )

    def charge_model_call(self) -> None:
        self._model_calls += 1
        if self._model_calls > self._budget.max_model_calls:
            raise BudgetExhausted(
                f"max_model_calls exceeded ({self._budget.max_model_calls}); "
                f"consumed {self.consumed}"
            )

    def charge_retry(self) -> None:
        self._retries += 1
        if self._retries > self._budget.max_retries:
            raise BudgetExhausted(
                f"max_retries exceeded ({self._budget.max_retries}); consumed {self.consumed}"
            )

    def check_time(self) -> None:
        if self._clock() - self._started > self._budget.max_seconds:
            raise BudgetExhausted(
                f"max_seconds exceeded ({self._budget.max_seconds}); consumed {self.consumed}"
            )
