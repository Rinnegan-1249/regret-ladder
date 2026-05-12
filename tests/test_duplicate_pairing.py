from __future__ import annotations

import pyspiel

from poker_ai.agents.always_call import AlwaysCallAgent
from poker_ai.agents.always_fold import AlwaysFoldAgent
from poker_ai.evaluation.tournament import duplicate_match


def test_duplicate_match_returns_requested_number_of_pairs():
    game = pyspiel.load_game("kuhn_poker")
    payoffs = duplicate_match(game, AlwaysCallAgent(), AlwaysFoldAgent(), n_pairs=25, base_seed=0)
    assert len(payoffs) == 25
