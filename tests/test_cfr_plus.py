import numpy as np
import pyspiel

from poker_ai.agents.cfr import VanillaCFR
from poker_ai.agents.cfr_plus import CFRPlus
from poker_ai.evaluation.exploitability import compute_exploitability


def test_cfr_plus_trains_without_crashing_and_policies_are_valid():
    game = pyspiel.load_game("kuhn_poker")
    solver = CFRPlus(game)
    solver.train(20)

    for policy in (solver.average_policy(), solver.current_policy()):
        for info_state, legal in solver.legal_actions_by_info_state.items():
            probs = policy.policy_for_key(info_state)
            assert np.all(np.asarray(probs) >= 0.0)
            assert abs(sum(probs[a] for a in legal) - 1.0) < 1e-9


def test_cfr_plus_regrets_stay_non_negative():
    game = pyspiel.load_game("kuhn_poker")
    solver = CFRPlus(game)
    solver.train(50)

    assert solver.regret_sum, "no infosets visited"
    for info_state, regrets in solver.regret_sum.items():
        assert np.all(regrets >= 0.0), f"negative regret at {info_state}"


def test_cfr_plus_beats_vanilla_cfr_at_equal_iterations():
    game = pyspiel.load_game("kuhn_poker")
    iters = 1_000

    cfr = VanillaCFR(game).train(iters)
    cfrp = CFRPlus(game).train(iters)

    cfr_expl = compute_exploitability(game, cfr.average_policy())
    cfrp_expl = compute_exploitability(game, cfrp.average_policy())

    assert cfrp_expl < 1e-2
    assert cfrp_expl < cfr_expl
