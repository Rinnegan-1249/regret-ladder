import numpy as np

from experiments.exp02_rps_convergence import run_self_play


def test_regret_matching_rps_converges_toward_uniform():
    rows = run_self_play(iterations=50_000, seed=7, log_every=50_000)

    final = rows[-1]

    p1_avg = np.array(
        [
            final["p1_avg_rock"],
            final["p1_avg_paper"],
            final["p1_avg_scissors"],
        ]
    )

    p2_avg = np.array(
        [
            final["p2_avg_rock"],
            final["p2_avg_paper"],
            final["p2_avg_scissors"],
        ]
    )

    uniform = np.full(3, 1.0 / 3.0)

    assert np.max(np.abs(p1_avg - uniform)) < 0.08
    assert np.max(np.abs(p2_avg - uniform)) < 0.08

    assert final["p1_avg_regret"] < 0.05
    assert final["p2_avg_regret"] < 0.05