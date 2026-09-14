import pytest

from pca.agent.limits import Budget, BudgetTracker
from pca.core.errors import BudgetExhausted


def test_action_budget_is_enforced() -> None:
    tracker = BudgetTracker(Budget(max_actions=2))
    tracker.charge_action()
    tracker.charge_action()
    with pytest.raises(BudgetExhausted, match="max_actions"):
        tracker.charge_action()


def test_model_call_budget_is_enforced() -> None:
    tracker = BudgetTracker(Budget(max_model_calls=1))
    tracker.charge_model_call()
    with pytest.raises(BudgetExhausted, match="max_model_calls"):
        tracker.charge_model_call()


def test_retry_budget_is_enforced() -> None:
    tracker = BudgetTracker(Budget(max_retries=1))
    tracker.charge_retry()
    with pytest.raises(BudgetExhausted, match="max_retries"):
        tracker.charge_retry()


def test_wall_clock_budget_uses_an_injectable_clock() -> None:
    ticks = iter([0.0, 1.0, 99.0])
    tracker = BudgetTracker(Budget(max_seconds=10.0), clock=lambda: next(ticks))
    tracker.check_time()
    with pytest.raises(BudgetExhausted, match="max_seconds"):
        tracker.check_time()


def test_cancellation_is_observable() -> None:
    tracker = BudgetTracker(Budget())
    assert tracker.cancelled is False
    tracker.cancel()
    assert tracker.cancelled is True


def test_consumption_is_reported_for_the_error_message() -> None:
    tracker = BudgetTracker(Budget())
    tracker.charge_action()
    tracker.charge_model_call()
    assert tracker.consumed == {"actions": 1, "model_calls": 1, "retries": 0}
