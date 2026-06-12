import pyspiel

from poker_ai.agents.cfr import VanillaCFR


def test_vanilla_cfr_trains_on_kuhn_without_crashing():
    game = pyspiel.load_game("kuhn_poker")
    cfr = VanillaCFR(game)

    cfr.train(10)

    policy = cfr.average_policy()
    assert policy is not None

    state = game.new_initial_state()
    while state.is_chance_node():
        state.apply_action(state.legal_actions()[0])

    probs = policy.action_probabilities(state)
    assert len(probs) > 0
    assert abs(sum(probs.values()) - 1.0) < 1e-9
