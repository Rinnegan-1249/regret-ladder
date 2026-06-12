import numpy as np
import pyspiel

from poker_ai.agents.mccfr_external import ExternalSamplingMCCFR
from poker_ai.agents.mccfr_outcome import OutcomeSamplingMCCFR
from poker_ai.evaluation.exploitability import compute_exploitability


def _assert_valid_policies(solver):
    for policy in (solver.average_policy(), solver.current_policy()):
        for info_state, legal in solver.legal_actions_by_info_state.items():
            probs = policy.policy_for_key(info_state)
            assert np.all(np.asarray(probs) >= 0.0)
            assert abs(sum(probs[a] for a in legal) - 1.0) < 1e-9


def test_outcome_sampling_trains_and_policies_are_valid():
    game = pyspiel.load_game("kuhn_poker")
    solver = OutcomeSamplingMCCFR(game, seed=0)
    solver.train(200)
    assert solver.nodes_touched > 0
    _assert_valid_policies(solver)


def test_external_sampling_trains_and_policies_are_valid():
    game = pyspiel.load_game("kuhn_poker")
    solver = ExternalSamplingMCCFR(game, seed=0)
    solver.train(200)
    assert solver.nodes_touched > 0
    _assert_valid_policies(solver)


def test_mccfr_seeded_runs_are_deterministic():
    game = pyspiel.load_game("kuhn_poker")
    for cls in (OutcomeSamplingMCCFR, ExternalSamplingMCCFR):
        a = cls(game, seed=123).train(300)
        b = cls(game, seed=123).train(300)
        assert set(a.regret_sum) == set(b.regret_sum)
        for info_state in a.regret_sum:
            assert np.allclose(a.regret_sum[info_state], b.regret_sum[info_state])


def test_mccfr_converges_on_kuhn():
    game = pyspiel.load_game("kuhn_poker")

    es = ExternalSamplingMCCFR(game, seed=0).train(20_000)
    assert compute_exploitability(game, es.average_policy()) < 0.02

    os_ = OutcomeSamplingMCCFR(game, seed=0).train(50_000)
    assert compute_exploitability(game, os_.average_policy()) < 0.05
