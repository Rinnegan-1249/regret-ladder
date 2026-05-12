from __future__ import annotations

import pyspiel

from poker_ai.agents.always_call import AlwaysCallAgent
from poker_ai.agents.always_fold import AlwaysFoldAgent
from poker_ai.agents.ev_heuristic import EVHeuristicAgent
from poker_ai.agents.random_agent import RandomAgent
from poker_ai.agents.rule_based import RuleBasedAgent


def test_week1_agents_choose_legal_actions_on_initial_decision():
    game = pyspiel.load_game("kuhn_poker")
    state = game.new_initial_state()

    # Apply chance actions until first player decision.
    while state.is_chance_node():
        action, _prob = state.chance_outcomes()[0]
        state.apply_action(action)

    agents = [
        RandomAgent(seed=0),
        AlwaysCallAgent(),
        AlwaysFoldAgent(),
        RuleBasedAgent(),
        EVHeuristicAgent(seed=0),
    ]

    legal = state.legal_actions()
    for agent in agents:
        assert agent.act(state) in legal, agent.name
