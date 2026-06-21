import numpy as np

from poker_ai.agents.regret_matching_plus import RegretMatchingPlusAgent
from poker_ai.env.rps import PAYOFF_MATRIX


def test_current_strategy_is_valid_distribution_at_init():
    agent = RegretMatchingPlusAgent(num_actions=3, seed=0)
    strategy = agent.current_strategy()

    assert strategy.shape == (3,)
    assert np.all(strategy >= 0.0)
    assert np.isclose(strategy.sum(), 1.0)


def test_regrets_never_go_negative():
    agent = RegretMatchingPlusAgent(num_actions=3, seed=0)
    agent.regret_sum[:] = agent.rng.uniform(0.0, 1.0, size=3)

    opponent = np.array([0.5, 0.3, 0.2])
    for _ in range(200):
        strategy = agent.current_strategy()
        utilities = PAYOFF_MATRIX @ opponent
        agent.update_expected(strategy, utilities)
        assert np.all(agent.regret_sum >= 0.0)
        assert np.all(strategy >= 0.0)
        assert np.isclose(strategy.sum(), 1.0)

    avg = agent.average_strategy()
    assert np.all(avg >= 0.0)
    assert np.isclose(avg.sum(), 1.0)


def test_self_play_converges_to_nash_faster_than_uniform_baseline():
    """Two CFR+ agents in self-play (expected-utility updates, the same
    setup exp02/exp02-equivalent self-play uses for plain regret matching)
    should converge to the (1/3, 1/3, 1/3) Nash equilibrium."""
    p1 = RegretMatchingPlusAgent(num_actions=3, seed=0)
    p2 = RegretMatchingPlusAgent(num_actions=3, seed=1)
    p1.regret_sum[:] = p1.rng.uniform(0.0, 1.0, size=3)
    p2.regret_sum[:] = p2.rng.uniform(0.0, 1.0, size=3)

    for _ in range(5000):
        s1, s2 = p1.current_strategy(), p2.current_strategy()
        p1.update_expected(s1, PAYOFF_MATRIX @ s2)
        p2.update_expected(s2, PAYOFF_MATRIX @ s1)

    avg1 = p1.average_strategy()
    assert np.allclose(avg1, [1 / 3, 1 / 3, 1 / 3], atol=0.02)
    assert p1.average_regret() < 1e-2
