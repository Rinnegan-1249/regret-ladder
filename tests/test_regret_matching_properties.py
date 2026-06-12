import numpy as np

from poker_ai.agents.regret_matching import RegretMatchingAgent
from poker_ai.env.rps import PAYOFF_MATRIX


def test_current_strategy_is_valid_distribution_at_init():
    agent = RegretMatchingAgent(num_actions=3, seed=0)
    strategy = agent.current_strategy()

    assert strategy.shape == (3,)
    assert np.all(strategy >= 0.0)
    assert np.isclose(strategy.sum(), 1.0)


def test_current_strategy_is_valid_distribution_after_updates():
    agent = RegretMatchingAgent(num_actions=3, seed=0)
    agent.regret_sum[:] = agent.rng.uniform(0.0, 1.0, size=3)

    opponent = np.array([0.5, 0.3, 0.2])

    for _ in range(100):
        strategy = agent.current_strategy()
        utilities = PAYOFF_MATRIX @ opponent
        agent.update_expected(strategy, utilities)

        assert np.all(strategy >= 0.0)
        assert np.isclose(strategy.sum(), 1.0)

    avg = agent.average_strategy()
    assert np.all(avg >= 0.0)
    assert np.isclose(avg.sum(), 1.0)
