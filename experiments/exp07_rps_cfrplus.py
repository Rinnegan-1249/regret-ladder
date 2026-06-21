"""CFR+ (regret-matching+) vs vanilla regret matching on Rock-Paper-Scissors.

Mirrors exp02's self-play setup (expected-utility updates, seeded
symmetry-breaking perturbation) for both poker_ai.agents.regret_matching.
RegretMatchingAgent and the new poker_ai.agents.regret_matching_plus.
RegretMatchingPlusAgent, then reports each algorithm's exploitability -
computed analytically from the known RPS payoff matrix (RPS is not a
pyspiel game, so there is no OpenSpiel reference solver to compare against
here, unlike Kuhn/Leduc).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from poker_ai.agents.regret_matching import RegretMatchingAgent
from poker_ai.agents.regret_matching_plus import RegretMatchingPlusAgent
from poker_ai.env.rps import PAYOFF_MATRIX

AGENTS = {
    "RM": RegretMatchingAgent,
    "CFR+": RegretMatchingPlusAgent,
}


def exploitability(s1: np.ndarray, s2: np.ndarray) -> float:
    """NashConv / 2 for a 2-player zero-sum normal-form game, computed
    exactly from the known payoff matrix (no sampling needed)."""
    p1_utilities = PAYOFF_MATRIX @ s2
    value_p1 = float(s1 @ p1_utilities)
    br1 = float(p1_utilities.max())

    p2_utilities = -(PAYOFF_MATRIX.T @ s1)
    value_p2 = float(s2 @ p2_utilities)
    br2 = float(p2_utilities.max())

    nash_conv = (br1 - value_p1) + (br2 - value_p2)
    return nash_conv / 2.0


def run_self_play(agent_cls, iterations: int, seed: int) -> dict:
    p1 = agent_cls(num_actions=3, seed=seed)
    p2 = agent_cls(num_actions=3, seed=seed + 10_000)
    p1.regret_sum[:] = p1.rng.uniform(0.0, 1.0, size=3)
    p2.regret_sum[:] = p2.rng.uniform(0.0, 1.0, size=3)

    for _ in range(iterations):
        s1, s2 = p1.current_strategy(), p2.current_strategy()
        p1.update_expected(s1, PAYOFF_MATRIX @ s2)
        p2.update_expected(s2, PAYOFF_MATRIX @ s1)

    avg1, avg2 = p1.average_strategy(), p2.average_strategy()
    return {
        "seed": seed,
        "iterations": iterations,
        "p1_avg_regret": p1.average_regret(),
        "p2_avg_regret": p2.average_regret(),
        "p1_avg_rock": float(avg1[0]), "p1_avg_paper": float(avg1[1]), "p1_avg_scissors": float(avg1[2]),
        "p2_avg_rock": float(avg2[0]), "p2_avg_paper": float(avg2[1]), "p2_avg_scissors": float(avg2[2]),
        "exploitability": exploitability(avg1, avg2),
    }


def frozen_strategy(agent_cls, iterations: int, seed: int = 0) -> np.ndarray:
    """A single agent's average strategy after self-play against its own
    mirrored opponent (seed+10_000) - the same convention web/bots.py uses
    for the website's frozen RM bot, so the round-robin below uses the
    actual strategies already deployed where applicable."""
    p1 = agent_cls(num_actions=3, seed=seed)
    p2 = agent_cls(num_actions=3, seed=seed + 10_000)
    p1.regret_sum[:] = p1.rng.uniform(0.0, 1.0, size=3)
    p2.regret_sum[:] = p2.rng.uniform(0.0, 1.0, size=3)
    for _ in range(iterations):
        s1, s2 = p1.current_strategy(), p2.current_strategy()
        p1.update_expected(s1, PAYOFF_MATRIX @ s2)
        p2.update_expected(s2, PAYOFF_MATRIX @ s1)
    return p1.average_strategy()


def run_round_robin(iterations: int, seed: int = 0) -> pd.DataFrame:
    """Exact round-robin payoff matrix among fixed RPS strategies - exact,
    not sampled, since payoff(A, B) = s_A @ PAYOFF_MATRIX @ s_B is a closed
    form given two fixed strategy vectors."""
    strategies = {
        "Uniform": np.full(3, 1.0 / 3.0),
        "RM": frozen_strategy(RegretMatchingAgent, iterations, seed),
        "CFR+": frozen_strategy(RegretMatchingPlusAgent, iterations, seed),
    }
    names = list(strategies)
    matrix = pd.DataFrame(np.zeros((len(names), len(names))), index=names, columns=names)
    for a in names:
        for b in names:
            matrix.loc[a, b] = float(strategies[a] @ PAYOFF_MATRIX @ strategies[b])
    return matrix


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=10_000)
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    parser.add_argument("--out-dir", type=str, default="results")
    args = parser.parse_args()

    rows = []
    for name, cls in AGENTS.items():
        for seed in args.seeds:
            row = run_self_play(cls, args.iterations, seed)
            row["algorithm"] = name
            rows.append(row)

    df = pd.DataFrame(rows)
    out_path = Path(args.out_dir) / "tables" / "exp07_rps_cfrplus.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

    print(f"Iterations: {args.iterations}  Seeds: {args.seeds}")
    summary = df.groupby("algorithm")[["exploitability", "p1_avg_regret"]].mean()
    print(summary)
    print(f"Saved CSV: {out_path}")

    matrix = run_round_robin(args.iterations, seed=args.seeds[0])
    rr_path = Path(args.out_dir) / "tables" / "exp07_rps_round_robin.csv"
    matrix.to_csv(rr_path)
    print("\nRound-robin payoff matrix (row's payoff vs column, exact):")
    print(matrix.round(4))
    print(f"Saved CSV: {rr_path}")


if __name__ == "__main__":
    main()
