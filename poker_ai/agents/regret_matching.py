from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class RegretMatchingAgent:
    """
    Regret matching agent for a normal-form game.

    For RPS:
        num_actions = 3

    Main state:
        regret_sum[a]   = cumulative regret for not playing action a
        strategy_sum[a] = cumulative strategy probability assigned to action a

    The average strategy is strategy_sum / iterations.
    """

    num_actions: int
    seed: int | None = None

    def __post_init__(self) -> None:
        if self.num_actions <= 0:
            raise ValueError("num_actions must be positive.")

        self.rng = np.random.default_rng(self.seed)
        self.regret_sum = np.zeros(self.num_actions, dtype=np.float64)
        self.strategy_sum = np.zeros(self.num_actions, dtype=np.float64)
        self.iterations = 0

    def current_strategy(self) -> np.ndarray:
        """
        Convert cumulative regrets into the next strategy using regret matching.

        sigma(a) proportional to max(regret_sum[a], 0).

        If all positive regrets are zero, return uniform strategy.
        """
        positive_regrets = np.maximum(self.regret_sum, 0.0)
        normalizer = positive_regrets.sum()

        if normalizer > 0:
            return positive_regrets / normalizer

        return np.full(self.num_actions, 1.0 / self.num_actions, dtype=np.float64)

    def sample_action(self, strategy: np.ndarray) -> int:
        """Sample one action according to the given strategy."""
        return int(self.rng.choice(self.num_actions, p=strategy))

    def update(
        self,
        strategy: np.ndarray,
        action: int,
        action_utilities: np.ndarray,
    ) -> None:
        """
        Update cumulative regrets and average-strategy accumulator.

        Args:
            strategy:
                Strategy used before sampling the action.

            action:
                Actual action sampled from the strategy.

            action_utilities:
                action_utilities[a] = payoff we would have received
                if we had played action a against the opponent's realized action.

        Regret update:
            regret_sum[a] += action_utilities[a] - action_utilities[action]
        """
        if strategy.shape != (self.num_actions,):
            raise ValueError("strategy has wrong shape.")

        if action_utilities.shape != (self.num_actions,):
            raise ValueError("action_utilities has wrong shape.")

        actual_utility = action_utilities[action]
        regrets_this_round = action_utilities - actual_utility

        self.regret_sum += regrets_this_round
        self.strategy_sum += strategy
        self.iterations += 1

    def update_expected(
        self,
        strategy: np.ndarray,
        action_utilities: np.ndarray,
    ) -> None:
        """
        Expected-utility regret update.

        Unlike update(), no action is sampled: the baseline is the expected
        utility of our own mixed strategy, and action_utilities are computed
        against the opponent's full strategy distribution.

        Args:
            strategy:
                Strategy played this iteration (the full distribution).

            action_utilities:
                action_utilities[a] = expected payoff of action a against
                the opponent's strategy distribution.

        Regret update:
            regret_sum[a] += action_utilities[a] - strategy @ action_utilities
        """
        if strategy.shape != (self.num_actions,):
            raise ValueError("strategy has wrong shape.")

        if action_utilities.shape != (self.num_actions,):
            raise ValueError("action_utilities has wrong shape.")

        expected_utility = float(strategy @ action_utilities)
        self.regret_sum += action_utilities - expected_utility
        self.strategy_sum += strategy
        self.iterations += 1

    def average_strategy(self) -> np.ndarray:
        """Return average strategy over all iterations so far."""
        if self.iterations == 0:
            return np.full(self.num_actions, 1.0 / self.num_actions, dtype=np.float64)

        avg = self.strategy_sum / self.iterations
        return avg / avg.sum()

    def average_regret(self) -> float:
        """
        Return average external regret.

        R_T / T = max_a positive cumulative regret(a) / T
        """
        if self.iterations == 0:
            return 0.0

        return float(max(0.0, self.regret_sum.max()) / self.iterations)