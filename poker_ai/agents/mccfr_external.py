"""External-sampling MCCFR for two-player zero-sum OpenSpiel games.

Implements external sampling from:
    Lanctot, Waugh, Zinkevich, Bowling, "Monte Carlo Sampling for Regret
    Minimization in Extensive Games", NIPS 2009.
    (Research_Papers/MCCFR_Lanctot2009.pdf)

Each iteration runs one pass per update player. Within a pass, the choices
EXTERNAL to the update player are sampled (chance by f_c, opponent actions
by sigma_{-i}), while ALL of the update player's actions are enumerated.
Because the sampled block probability is q(z) = pi_{-i}(z), the
counterfactual weighting cancels exactly and the paper's Eq. (11) update
reduces to

    r(I, a) += u(a) - u,    u = sum_a sigma(a|I) * u(a),

with the u-values being sampled returns. Average-strategy contributions
are accumulated at opponent infosets as s(I, a) += sigma(a|I) per visit
("simple" averaging, the standard two-player rule).
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
from open_spiel.python import policy as os_policy


def _child(state, action: int):
    child = state.clone()
    child.apply_action(int(action))
    return child


class ExternalSamplingMCCFR:
    def __init__(self, game, seed: int | None = None):
        if game.num_players() != 2:
            raise ValueError("This program supports only two-player games.")
        self.game = game
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

    def _pass(self, state, update_player: int) -> float:
        """One external-sampling traversal; returns the sampled value of
        this state for update_player."""
        self.nodes_touched += 1

        if state.is_terminal():
            return float(state.player_return(update_player))

        if state.is_chance_node():
            actions, probs = zip(*state.chance_outcomes())
            probs = np.asarray(probs, dtype=np.float64)
            probs = probs / probs.sum()
            k = int(self.rng.choice(len(actions), p=probs))
            return self._pass(_child(state, actions[k]), update_player)

        player = state.current_player()
        legal_actions = list(state.legal_actions())
        info_state = state.information_state_string(player)
        strategy = self._strategy(info_state, legal_actions)

        if player == update_player:
            # Enumerate all own actions (Eq. 11).
            child_values = np.zeros(self.num_actions, dtype=np.float64)
            value = 0.0
            for a in legal_actions:
                child_values[a] = self._pass(_child(state, a), update_player)
                value += strategy[a] * child_values[a]
            for a in legal_actions:
                self.regret_sum[info_state][a] += child_values[a] - value
            return value

        # Opponent node: sample one action by sigma_{-i}; accumulate the
        # opponent's average strategy (simple averaging).
        for a in legal_actions:
            self.strategy_sum[info_state][a] += strategy[a]
        sample_probs = np.array([strategy[a] for a in legal_actions])
        sample_probs = sample_probs / sample_probs.sum()
        k = int(self.rng.choice(len(legal_actions), p=sample_probs))
        return self._pass(_child(state, legal_actions[k]), update_player)

    def step(self):
        """One iteration: one external-sampling pass per update player."""
        self.iteration += 1
        for update_player in range(self.num_players):
            self._pass(self.game.new_initial_state(), update_player)

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
