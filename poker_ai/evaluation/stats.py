from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass(frozen=True)
class MatchStats:
    n: int
    mean: float
    std: float
    ci_low: float
    ci_high: float
    win_rate: float
    p_value_vs_zero: float


def summarize_payoffs(payoffs: np.ndarray) -> MatchStats:
    payoffs = np.asarray(payoffs, dtype=float)
    n = int(payoffs.size)
    mean = float(payoffs.mean()) if n else float("nan")
    std = float(payoffs.std(ddof=1)) if n > 1 else 0.0
    se = std / math.sqrt(n) if n > 1 else 0.0
    half_width = 1.96 * se
    win_rate = float((payoffs > 0).mean()) if n else float("nan")

    if n > 1 and std > 0:
        _t, p_value = stats.ttest_1samp(payoffs, popmean=0.0)
        p_value = float(p_value)
    else:
        p_value = float("nan")

    return MatchStats(
        n=n,
        mean=mean,
        std=std,
        ci_low=mean - half_width,
        ci_high=mean + half_width,
        win_rate=win_rate,
        p_value_vs_zero=p_value,
    )
