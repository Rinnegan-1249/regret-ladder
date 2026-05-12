from __future__ import annotations

from poker_ai.agents.base import Agent


class AlwaysCallAgent(Agent):
    """Always chooses the aggressive/call-like poker action when available.

    In OpenSpiel's small poker games, action 1 is usually bet/call and action 0 is pass/fold.
    This is a crude baseline, not a strategically meaningful bot.
    """

    name = "always_call"

    def act(self, state) -> int:
        legal = state.legal_actions()
        return 1 if 1 in legal else int(legal[0])
