"""CFR+ for two-player zero-sum OpenSpiel games.

Implements the algorithm from:
    Oskari Tammelin, "Solving Large Imperfect Information Games Using CFR+",
    arXiv:1407.5042, 2014. (Research_Papers/CFRplus_Tammelin2014.pdf)

CFR+ differs from vanilla CFR in three ways:

1. Regret-matching+: cumulative regrets are floored at zero after every
   update,
       R+[I][a] <- max(R+[I][a] + (v(a) - v), 0),
   so stored regrets are always non-negative and the next strategy is
   directly proportional to them.

2. Alternating updates: each iteration runs two passes. The pass for
   player i updates only player i's regrets (at i's information sets)
   and accumulates the opponent's average-strategy contribution (at the
   opponent's information sets), following Algorithm 1 of the paper.

3. Weighted averaging: average-strategy contributions on iteration t are
   weighted by w_t = max(t - d, 0), where d is the averaging delay.
   With d = 0 this is linear averaging.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
from open_spiel.python import policy as os_policy


def _child(state, action: int):
    child = state.clone()
    child.apply_action(int(action))
    return child


class CFRPlus:
    def __init__(self, game, delay: int = 0):
        if game.num_players() != 2:
            raise ValueError("This program supports only two-player games.")
        if delay < 0:
            raise ValueError("delay must be non-negative.")
        self.game = game
        self.delay = delay
        self.num_players = game.num_players()
        self.num_actions = game.num_distinct_actions()
        # Regret-matching+ tables: entries are always >= 0.
        self.regret_sum = defaultdict(lambda: np.zeros(self.num_actions, dtype=np.float64))
        self.strategy_sum = defaultdict(lambda: np.zeros(self.num_actions, dtype=np.float64))
        self.legal_actions_by_info_state: dict[str, list[int]] = {}
        self.iteration = 0

    def _strategy(self, info_state: str, legal_actions) -> np.ndarray:
        """Regret-matching+ strategy: proportional to the stored regrets.

        No max(., 0) is needed because regret-matching+ keeps the stored
        regrets non-negative at all times.
        """
        self.legal_actions_by_info_state[info_state] = list(legal_actions)

        strategy = np.zeros(self.num_actions, dtype=np.float64)
        regrets = self.regret_sum[info_state]
        normalizer = sum(regrets[a] for a in legal_actions)

        if normalizer > 0:
            for a in legal_actions:
                strategy[a] = regrets[a] / normalizer
        else:
            for a in legal_actions:
                strategy[a] = 1.0 / len(legal_actions)

        return strategy

    def _pass(
        self,
        state,
        update_player: int,
        reach_probs: np.ndarray,
        chance_reach: float,
        weight: float,
        delta_regret,
    ) -> np.ndarray:
        """One alternating-update tree walk for update_player.

        Returns the vector utility [player0, player1] of this state.

        Regret increments for update_player are accumulated into
        delta_regret and applied (with the + floor) after the walk, so the
        strategy used within one pass is consistent across the multiple
        histories of an information set (vector-form behavior).

        At opponent nodes the opponent's average-strategy table is updated
        with weight w (Algorithm 1, line 37).
        """
        if state.is_terminal():
            return np.asarray(state.returns(), dtype=np.float64)

        if state.is_chance_node():
            node_util = np.zeros(self.num_players, dtype=np.float64)
            for action, prob in state.chance_outcomes():
                node_util += prob * self._pass(
                    _child(state, action),
                    update_player,
                    reach_probs,
                    chance_reach * prob,
                    weight,
                    delta_regret,
                )
            return node_util

        player = state.current_player()
        legal_actions = list(state.legal_actions())
        info_state = state.information_state_string(player)
        strategy = self._strategy(info_state, legal_actions)

        action_utils: dict[int, np.ndarray] = {}
        node_util = np.zeros(self.num_players, dtype=np.float64)

        for action in legal_actions:
            next_reach = reach_probs.copy()
            next_reach[player] *= strategy[action]
            action_utils[action] = self._pass(
                _child(state, action),
                update_player,
                next_reach,
                chance_reach,
                weight,
                delta_regret,
            )
            node_util += strategy[action] * action_utils[action]

        if player == update_player:
            opponent = 1 - player
            counterfactual_reach = chance_reach * reach_probs[opponent]
            for action in legal_actions:
                regret = action_utils[action][player] - node_util[player]
                delta_regret[info_state][action] += counterfactual_reach * regret
        else:
            # Opponent node: accumulate the opponent's average strategy,
            # weighted by its own reach probability and w_t.
            for action in legal_actions:
                self.strategy_sum[info_state][action] += (
                    reach_probs[player] * strategy[action] * weight
                )

        return node_util

    def step(self) -> np.ndarray:
        """One CFR+ iteration: an alternating pass for each player."""
        self.iteration += 1
        weight = float(max(self.iteration - self.delay, 0))

        value = np.zeros(self.num_players, dtype=np.float64)
        for update_player in range(self.num_players):
            delta_regret = defaultdict(
                lambda: np.zeros(self.num_actions, dtype=np.float64)
            )
            value = self._pass(
                self.game.new_initial_state(),
                update_player,
                np.ones(self.num_players, dtype=np.float64),
                1.0,
                weight,
                delta_regret,
            )
            # Regret-matching+ floor: stored regrets never go negative.
            for info_state, values in delta_regret.items():
                self.regret_sum[info_state] = np.maximum(
                    self.regret_sum[info_state] + values, 0.0
                )

        return value

    def train(self, iterations: int):
        for _ in range(iterations):
            self.step()
        return self

    def average_policy(self):
        """OpenSpiel TabularPolicy from the weighted cumulative strategy."""
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
        """OpenSpiel TabularPolicy from the current regret-matching+ strategy."""
        tabular = os_policy.TabularPolicy(self.game)
        for info_state, legal_actions in self.legal_actions_by_info_state.items():
            probs = tabular.policy_for_key(info_state)
            probs[:] = self._strategy(info_state, legal_actions)
        return tabular
