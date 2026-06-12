"""Vanilla tabular CFR for two-player zero-sum OpenSpiel games.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

import numpy as np
from open_spiel.python import policy as os_policy


def _child(state, action: int):
    child = state.clone()
    child.apply_action(int(action))
    return child


class VanillaCFR:
    def __init__(self, game):
        if game.num_players() != 2:
            raise ValueError("This program supports only two-player games.")
        self.game = game
        self.num_players = game.num_players()
        self.num_actions = game.num_distinct_actions()
        self.regret_sum = defaultdict(lambda: np.zeros(self.num_actions, dtype=np.float64))
        self.strategy_sum = defaultdict(lambda: np.zeros(self.num_actions, dtype=np.float64))
        self.legal_actions_by_info_state: dict[str, list[int]] = {}
        self.iteration = 0

    def _strategy_from_table(self, regret_table, info_state, legal_actions):
        self.legal_actions_by_info_state[info_state] = list(legal_actions)

        strategy = np.zeros(self.num_actions, dtype=np.float64)
        positive_regrets = np.maximum(regret_table[info_state], 0.0)
        normalizer = sum(positive_regrets[a] for a in legal_actions)

        if normalizer > 0:
            for a in legal_actions:
                strategy[a] = positive_regrets[a] / normalizer
        else:
            for a in legal_actions:
                strategy[a] = 1.0 / len(legal_actions)

        return strategy

    def _cfr(
    self,
    state,
    reach_probs: np.ndarray,
    chance_reach: float,
    frozen_regret,
    delta_regret,
    delta_strategy,
) -> np.ndarray:
        """Returns vector utility for [player0, player1] from this state.

        reach_probs[i] is player i's contribution to reaching this state.
        chance_reach is chance's contribution.

        frozen_regret is the regret table frozen at the start of this CFR iteration.
        delta_regret stores regret increments for this iteration.
        delta_strategy stores average-strategy increments for this iteration.
        """
        if state.is_terminal():
            return np.asarray(state.returns(), dtype=np.float64)

        if state.is_chance_node():
            node_util = np.zeros(self.num_players, dtype=np.float64)

            for action, prob in state.chance_outcomes():
                node_util += prob * self._cfr(
                    _child(state, action),
                    reach_probs,
                    chance_reach * prob,
                    frozen_regret,
                    delta_regret,
                    delta_strategy,
                )

            return node_util

        player = state.current_player()
        legal_actions = list(state.legal_actions())
        info_state = state.information_state_string(player)

        strategy = self._strategy_from_table(
            frozen_regret,
            info_state,
            legal_actions,
        )

        action_utils: dict[int, np.ndarray] = {}
        node_util = np.zeros(self.num_players, dtype=np.float64)

        for action in legal_actions:
            next_reach = reach_probs.copy()
            next_reach[player] *= strategy[action]

            action_utils[action] = self._cfr(
                _child(state, action),
                next_reach,
                chance_reach,
                frozen_regret,
                delta_regret,
                delta_strategy,
            )

            node_util += strategy[action] * action_utils[action]

        opponent = 1 - player
        counterfactual_reach = chance_reach * reach_probs[opponent]
        realization_weight = chance_reach * reach_probs[player]

        for action in legal_actions:
            regret = action_utils[action][player] - node_util[player]

            delta_regret[info_state][action] += counterfactual_reach * regret
            delta_strategy[info_state][action] += realization_weight * strategy[action]

        return node_util

    def step(self) -> np.ndarray:
        frozen_regret = defaultdict(
            lambda: np.zeros(self.num_actions, dtype=np.float64)
        )

        for info_state, regrets in self.regret_sum.items():
            frozen_regret[info_state] = regrets.copy()

        delta_regret = defaultdict(
            lambda: np.zeros(self.num_actions, dtype=np.float64)
        )

        delta_strategy = defaultdict(
            lambda: np.zeros(self.num_actions, dtype=np.float64)
        )

        root = self.game.new_initial_state()

        value = self._cfr(
            root,
            np.ones(self.num_players, dtype=np.float64),
            1.0,
            frozen_regret,
            delta_regret,
            delta_strategy,
        )

        for info_state, values in delta_regret.items():
            self.regret_sum[info_state] += values

        for info_state, values in delta_strategy.items():
            self.strategy_sum[info_state] += values

        self.iteration += 1
        return value

    def train(self, iterations: int):
        for _ in range(iterations):
            self.step()
        return self

    def average_policy(self):
        """Builds an OpenSpiel TabularPolicy from cumulative average strategy."""
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
        tabular = os_policy.TabularPolicy(self.game)

        for info_state, legal_actions in self.legal_actions_by_info_state.items():
            probs = tabular.policy_for_key(info_state)
            probs[:] = self._strategy_from_table(
                self.regret_sum,
                info_state,
                legal_actions,
            )

        return tabular


@dataclass
class PolicyAgent:
    """Samples actions from an OpenSpiel Policy object."""
    game: object
    policy: object
    name: str = "PolicyAgent"

    def act(self, state, rng: Optional[np.random.Generator] = None) -> int:
        rng = rng if rng is not None else np.random.default_rng()
        player = state.current_player()
        legal = list(state.legal_actions())
        action_probs = self.policy.action_probabilities(state, player)
        probs = np.asarray([action_probs.get(a, 0.0) for a in legal], dtype=np.float64)
        total = probs.sum()
        if total <= 0:
            probs = np.ones(len(legal), dtype=np.float64) / len(legal)
        else:
            probs = probs / total
        return int(rng.choice(legal, p=probs))
