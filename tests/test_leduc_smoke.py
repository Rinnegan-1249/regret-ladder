"""Smoke tests: all four CFR-family solvers on Leduc Poker.

Each test trains for 20 iterations and verifies the policy is well-formed
(probabilities non-negative and summing to 1 at every infoset).
"""
import numpy as np
import pyspiel
import pytest

from poker_ai.agents.cfr import VanillaCFR
from poker_ai.agents.cfr_plus import CFRPlus
from poker_ai.agents.mccfr_external import ExternalSamplingMCCFR
from poker_ai.agents.mccfr_outcome import OutcomeSamplingMCCFR


@pytest.fixture(scope="module")
def leduc():
    return pyspiel.load_game("leduc_poker")


def _assert_valid_policies(solver):
    for policy in (solver.average_policy(), solver.current_policy()):
        for info_state, legal in solver.legal_actions_by_info_state.items():
            probs = policy.policy_for_key(info_state)
            assert np.all(np.asarray(probs) >= 0.0)
            assert abs(sum(probs[a] for a in legal) - 1.0) < 1e-9


def test_vanilla_cfr_on_leduc(leduc):
    solver = VanillaCFR(leduc)
    solver.train(20)
    assert len(solver.legal_actions_by_info_state) > 0
    _assert_valid_policies(solver)


def test_cfr_plus_on_leduc(leduc):
    solver = CFRPlus(leduc)
    solver.train(20)
    # CFR+ regrets must never go negative
    for regrets in solver.regret_sum.values():
        assert np.all(regrets >= -1e-12)
    _assert_valid_policies(solver)


def test_outcome_sampling_on_leduc(leduc):
    solver = OutcomeSamplingMCCFR(leduc, seed=0)
    solver.train(20)
    assert solver.nodes_touched > 0
    _assert_valid_policies(solver)


def test_external_sampling_on_leduc(leduc):
    solver = ExternalSamplingMCCFR(leduc, seed=0)
    solver.train(20)
    assert solver.nodes_touched > 0
    _assert_valid_policies(solver)
