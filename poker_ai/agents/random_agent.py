from __future__ import annotations

import numpy as np

from poker_ai.agents.base import Agent


class RandomAgent(Agent):
    name = "random"

    def __init__(self, seed: int | None = None):
        self.rng = np.random.default_rng(seed)

    def act(self, state) -> int:
        legal = state.legal_actions()
        return int(self.rng.choice(legal))
