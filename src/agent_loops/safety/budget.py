"""Token budget tracking and enforcement (FR-SL-001)."""

from __future__ import annotations

import sys
from ..models import BudgetEntry, BudgetStatus
from ..state import StateManager


class BudgetTracker:
    """Track cumulative token usage and cost. Enforce hard spending caps."""

    WARNING_THRESHOLD = 0.80

    def __init__(self, budget_usd: float, state: StateManager) -> None:
        self.budget_usd = budget_usd
        self.state = state
        self._cumulative_cost = state.get_cumulative_cost()

    def record(self, iteration: int, cost_usd: float, input_tokens: int, output_tokens: int) -> None:
        self._cumulative_cost += cost_usd
        entry = BudgetEntry(
            iteration=iteration,
            cost_usd=cost_usd,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cumulative_cost_usd=self._cumulative_cost,
        )
        self.state.append_budget(entry)

    def check(self) -> BudgetStatus:
        if self._cumulative_cost >= self.budget_usd:
            return BudgetStatus.EXCEEDED
        if self._cumulative_cost >= self.budget_usd * self.WARNING_THRESHOLD:
            print(
                f"[WARNING] Budget at {self._cumulative_cost:.2f}/{self.budget_usd:.2f} USD "
                f"({self._cumulative_cost / self.budget_usd * 100:.0f}%)",
                file=sys.stderr,
            )
            return BudgetStatus.WARNING
        return BudgetStatus.OK

    @property
    def cumulative_cost(self) -> float:
        return self._cumulative_cost

    @property
    def remaining(self) -> float:
        return max(0.0, self.budget_usd - self._cumulative_cost)
