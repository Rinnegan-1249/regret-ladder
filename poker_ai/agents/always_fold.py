from __future__ import annotations

from poker_ai.agents.base import Agent


class AlwaysFoldAgent(Agent):
    """Always chooses the passive/fold-like poker action when available.

    In OpenSpiel's small poker games, action 0 is usually pass/fold.
    """

    name = "always_fold"

    def act(self, state) -> int:
        legal = state.legal_actions()
        return 0 if 0 in legal else int(legal[0])
