"""Regret-matching+ on Rock-Paper-Scissors - the CFR+ idea applied directly
to a normal-form game (a single information set per player).

CFR+ (poker_ai/agents/cfr_plus.py; Tammelin 2014,
Research_Papers/CFRplus_Tammelin2014.pdf) differs from vanilla CFR in three
ways: regret-matching+ (cumulative regrets floored at zero after every
update), alternating updates, and linearly weighted averaging. On a
normal-form game there is no extensive-form tree to walk and no sequential
turns to alternate over - "CFR+ on RPS" is exactly self-play with the first
and third of those changes:

    1. Regret-matching+: R+[a] <- max(R+[a] + (u(a) - u_strategy), 0).
    2. Weighted averaging: strategy_sum[a] += w_t * strategy[a],
       w_t = t (linear weighting, delay d = 0 - same default CFR+ uses).

This is a new, additive agent - it does not change RegretMatchingAgent's
existing update()/update_expected() behavior.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class RegretMatchingPlusAgent:
    """Regret-matching+ for a normal-form game.

    Main state:
        regret_sum[a]   = cumulative regret for not playing action a,
                          floored at zero after every update (always >= 0).
        strategy_sum[a] = cumulative strategy probability assigned to
                          action a, weighted linearly by iteration number.
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
        """Regret-matching+ strategy: proportional to the stored regrets.

        No max(., 0) is needed - regret-matching+ keeps regret_sum
        non-negative at all times (see update_expected).
        """
        normalizer = self.regret_sum.sum()
        if normalizer > 0:
            return self.regret_sum / normalizer
        return np.full(self.num_actions, 1.0 / self.num_actions, dtype=np.float64)

    def sample_action(self, strategy: np.ndarray) -> int:
        """Sample one action according to the given strategy."""
        return int(self.rng.choice(self.num_actions, p=strategy))

    def update_expected(
        self,
        strategy: np.ndarray,
        action_utilities: np.ndarray,
    ) -> None:
        """
        Expected-utility regret-matching+ update (self-play setting, mirrors
        RegretMatchingAgent.update_expected's signature/semantics exactly,
        except regrets are floored and averaging is linearly weighted).

        Regret update:
            regret_sum[a] = max(regret_sum[a] + action_utilities[a]
                                 - strategy @ action_utilities, 0)
        """
        if strategy.shape != (self.num_actions,):
            raise ValueError("strategy has wrong shape.")
        if action_utilities.shape != (self.num_actions,):
            raise ValueError("action_utilities has wrong shape.")

        self.iterations += 1
        expected_utility = float(strategy @ action_utilities)
        self.regret_sum = np.maximum(
            self.regret_sum + (action_utilities - expected_utility), 0.0
        )
        weight = float(self.iterations)  # linear averaging, delay d = 0
        self.strategy_sum += weight * strategy

    def average_strategy(self) -> np.ndarray:
        """Return the weighted-average strategy over all iterations so far."""
        if self.iterations == 0:
            return np.full(self.num_actions, 1.0 / self.num_actions, dtype=np.float64)
        total = self.strategy_sum.sum()
        if total > 0:
            return self.strategy_sum / total
        return np.full(self.num_actions, 1.0 / self.num_actions, dtype=np.float64)

    def average_regret(self) -> float:
        """
        Return average external regret.

        R_T / T = max_a regret_sum(a) / T (already non-negative; no
        max(0, .) needed since regret-matching+ floors every update).
        """
        if self.iterations == 0:
            return 0.0
        return float(self.regret_sum.max() / self.iterations)
