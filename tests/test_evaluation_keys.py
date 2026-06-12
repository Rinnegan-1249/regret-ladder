import numpy as np

from poker_ai.evaluation.stats import MatchStats, summarize_payoffs
from poker_ai.evaluation.tournament import summarize_samples


def test_summarize_payoffs_returns_expected_fields():
    payoffs = np.array([1.0, -1.0, 2.0, 0.5, -0.5])
    result = summarize_payoffs(payoffs)

    assert isinstance(result, MatchStats)
    assert result.n == 5
    for field in ("n", "mean", "std", "ci_low", "ci_high", "win_rate", "p_value_vs_zero"):
        assert hasattr(result, field)
    assert result.ci_low <= result.mean <= result.ci_high
    assert 0.0 <= result.win_rate <= 1.0


def test_summarize_samples_returns_expected_fields():
    samples = np.array([1.0, -1.0, 2.0, 0.5, -0.5])
    result = summarize_samples("agent_a", "agent_b", samples, seeds=[0, 1])

    for field in ("agent_a", "agent_b", "mean", "ci_low", "ci_high", "p_value", "n", "seeds"):
        assert hasattr(result, field)
    assert result.n == 5
    assert result.ci_low <= result.mean <= result.ci_high
