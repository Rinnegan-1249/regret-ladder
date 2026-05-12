from __future__ import annotations

import numpy as np

from poker_ai.agents.base import Agent
from poker_ai.agents.rule_based import _private_card_from_info_state


class EVHeuristicAgent(Agent):
    """A first 'principled' heuristic agent for Week 1.

    This is not a full counterfactual EV enumerator yet. It is a bridge baseline:
    it treats stronger private cards as higher equity and uses a mixed action for
    middle cards. Replace this with a true enumerative EV agent once the tournament
    runner is stable.
    """

    name = "ev_heuristic_v0"

    def __init__(self, seed: int | None = None):
        self.rng = np.random.default_rng(seed)

    def act(self, state) -> int:
        player = state.current_player()
        info = state.information_state_string(player)
        card = _private_card_from_info_state(info)
        legal = state.legal_actions()

        passive = 0 if 0 in legal else int(legal[0])
        aggressive = 1 if 1 in legal else int(legal[-1])

        if card is None:
            return int(self.rng.choice(legal))

        if card >= 2:
            return aggressive
        if card == 1:
            return aggressive if self.rng.random() < 0.35 else passive
        return passive
