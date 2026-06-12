"""Outcome-sampling MCCFR for two-player zero-sum OpenSpiel games.

Implements outcome sampling from:
    Lanctot, Waugh, Zinkevich, Bowling, "Monte Carlo Sampling for Regret
    Minimization in Extensive Games", NIPS 2009.
    (Research_Papers/MCCFR_Lanctot2009.pdf)

Each iteration samples ONE terminal history per update player using a
sampling profile sigma':
    - at the update player's infosets: epsilon-greedy,
      sigma' = epsilon * uniform + (1 - epsilon) * sigma  (paper: eps = 0.6),
    - at opponent infosets and chance nodes: on-policy (sigma / f_c).

Regret updates follow the recursion-friendly alternative form of the
paper's Eq. (10) (the form the paper recommends for implementation, also
used by OpenSpiel): child values are importance-corrected by the sample
probability, so at the update player's infosets

    r(I, a) += (opp_reach / sample_reach) * (child_value(a) - value),

which matches Eq. (10) in expectation. Average-strategy contributions are
accumulated at the update player's infosets with stochastic weighting
my_reach * sigma(a|I) / sample_reach (unbiased estimate of Eq. (3)'s
numerator).
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
from open_spiel.python import policy as os_policy


class OutcomeSamplingMCCFR:
    def __init__(self, game, epsilon: float = 0.6, seed: int | None = None):
        if game.num_players() != 2:
            raise ValueError("This program supports only two-player games.")
        if not 0.0 < epsilon <= 1.0:
            raise ValueError("epsilon must be in (0, 1] so q(z) >= delta > 0.")
        self.game = game
        self.epsilon = epsilon
        self.rng = np.random.default_rng(seed)
        self.num_players = game.num_players()
        self.num_actions = game.num_distinct_actions()
        self.regret_sum = defaultdict(lambda: np.zeros(self.num_actions, dtype=np.float64))
        self.strategy_sum = defaultdict(lambda: np.zeros(self.num_actions, dtype=np.float64))
        self.legal_actions_by_info_state: dict[str, list[int]] = {}
        self.iteration = 0
        self.nodes_touched = 0

    def _strategy(self, info_state: str, legal_actions) -> np.ndarray:
        """Standard regret matching: proportional to positive regrets."""
        self.legal_actions_by_info_state[info_state] = list(legal_actions)

        strategy = np.zeros(self.num_actions, dtype=np.float64)
        positive = np.maximum(self.regret_sum[info_state], 0.0)
        normalizer = sum(positive[a] for a in legal_actions)

        if normalizer > 0:
            for a in legal_actions:
                strategy[a] = positive[a] / normalizer
        else:
            for a in legal_actions:
                strategy[a] = 1.0 / len(legal_actions)

        return strategy

    def _episode(
        self,
        state,
        update_player: int,
        my_reach: float,
        opp_reach: float,
        sample_reach: float,
    ) -> float:
        """Samples one history; returns the importance-corrected value
        estimate of this state for update_player."""
        self.nodes_touched += 1

        if state.is_terminal():
            return float(state.player_return(update_player))

        if state.is_chance_node():
            actions, probs = zip(*state.chance_outcomes())
            probs = np.asarray(probs, dtype=np.float64)
            probs = probs / probs.sum()
            k = int(self.rng.choice(len(actions), p=probs))
            state.apply_action(int(actions[k]))
            return self._episode(
                state, update_player, my_reach,
                opp_reach * probs[k], sample_reach * probs[k],
            )

        player = state.current_player()
        legal_actions = list(state.legal_actions())
        info_state = state.information_state_string(player)
        strategy = self._strategy(info_state, legal_actions)

        if player == update_player:
            # Epsilon-greedy sampling profile keeps q(z) >= delta > 0.
            uniform = 1.0 / len(legal_actions)
            sample_probs = np.array(
                [self.epsilon * uniform + (1.0 - self.epsilon) * strategy[a]
                 for a in legal_actions]
            )
        else:
            sample_probs = np.array([strategy[a] for a in legal_actions])
        sample_probs = sample_probs / sample_probs.sum()

        k = int(self.rng.choice(len(legal_actions), p=sample_probs))
        sampled_action = legal_actions[k]

        if player == update_player:
            new_my_reach = my_reach * strategy[sampled_action]
            new_opp_reach = opp_reach
        else:
            new_my_reach = my_reach
            new_opp_reach = opp_reach * strategy[sampled_action]
        new_sample_reach = sample_reach * sample_probs[k]

        state.apply_action(sampled_action)
        child_value = self._episode(
            state, update_player, new_my_reach, new_opp_reach, new_sample_reach
        )

        # Importance-corrected child values: only the sampled branch has a
        # non-zero estimate (zero baseline), scaled by 1/sample_prob.
        child_values = np.zeros(self.num_actions, dtype=np.float64)
        child_values[sampled_action] = child_value / sample_probs[k]
        value_estimate = sum(strategy[a] * child_values[a] for a in legal_actions)

        if player == update_player:
            cf_value = value_estimate * opp_reach / sample_reach
            for a in legal_actions:
                cf_action_value = child_values[a] * opp_reach / sample_reach
                self.regret_sum[info_state][a] += cf_action_value - cf_value
            for a in legal_actions:
                self.strategy_sum[info_state][a] += (
                    my_reach * strategy[a] / sample_reach
                )

        return value_estimate

    def step(self):
        """One iteration: one sampled episode per update player."""
        self.iteration += 1
        for update_player in range(self.num_players):
            self._episode(
                self.game.new_initial_state(), update_player,
                my_reach=1.0, opp_reach=1.0, sample_reach=1.0,
            )

    def train(self, iterations: int):
        for _ in range(iterations):
            self.step()
        return self

    def average_policy(self):
        """OpenSpiel TabularPolicy from the cumulative average strategy."""
        tabular = os_policy.TabularPolicy(self.game)
        for info_state, legal_actions in self.legal_actions_by_info_state.items():
            probs = tabular.policy_for_key(info_state)
            probs[:] = 0.0
            normalizer = sum(self.strategy_sum[info_state][a] for a in legal_actions)
            if normalizer > 0:
                for action in legal_actions:
                    probs[action] = self.strategy_sum[info_state][action] / normalizer
            else:
                for action in legal_actions:
                    probs[action] = 1.0 / len(legal_actions)
        return tabular

    def current_policy(self):
        """OpenSpiel TabularPolicy from the current regret-matching strategy."""
        tabular = os_policy.TabularPolicy(self.game)
        for info_state, legal_actions in self.legal_actions_by_info_state.items():
            probs = tabular.policy_for_key(info_state)
            probs[:] = self._strategy(info_state, legal_actions)
        return tabular
