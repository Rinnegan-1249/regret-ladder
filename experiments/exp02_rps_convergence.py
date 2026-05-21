from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from poker_ai.agents.regret_matching import RegretMatchingAgent
from poker_ai.env.rps import ACTIONS, PAYOFF_MATRIX


def run_self_play(
    iterations: int,
    seed: int,
    log_every: int,
) -> list[dict]:
    """
    Run regret matching self-play on Rock-Paper-Scissors.

    Both players use regret matching.

    Returns:
        List of logged rows.
    """
    if iterations <= 0:
        raise ValueError("iterations must be positive.")

    if log_every <= 0:
        raise ValueError("log_every must be positive.")

    p1 = RegretMatchingAgent(num_actions=3, seed=seed)
    p2 = RegretMatchingAgent(num_actions=3, seed=seed + 10_000)

    uniform = np.full(3, 1.0 / 3.0)
    rows: list[dict] = []

    for t in range(1, iterations + 1):
        # 1. Each player computes strategy from cumulative regrets.
        p1_strategy = p1.current_strategy()
        p2_strategy = p2.current_strategy()

        # 2. Each player samples action.
        p1_action = p1.sample_action(p1_strategy)
        p2_action = p2.sample_action(p2_strategy)

        # 3. For player 1:
        #    action_utilities_p1[a] = payoff if P1 had played action a
        #    against P2's realized action.
        action_utilities_p1 = PAYOFF_MATRIX[:, p2_action].copy()

        # 4. For player 2:
        #    action_utilities_p2[a] = payoff if P2 had played action a
        #    against P1's realized action.
        #
        # Since PAYOFF_MATRIX is from row player's perspective:
        # payoff to P2 for action a against P1 action p1_action
        # equals PAYOFF_MATRIX[a, p1_action].
        action_utilities_p2 = PAYOFF_MATRIX[:, p1_action].copy()

        # 5. Update regret tables.
        p1.update(p1_strategy, p1_action, action_utilities_p1)
        p2.update(p2_strategy, p2_action, action_utilities_p2)

        # 6. Log progress.
        if t == 1 or t % log_every == 0 or t == iterations:
            p1_avg = p1.average_strategy()
            p2_avg = p2.average_strategy()

            row = {
                "iteration": t,
                "p1_avg_regret": p1.average_regret(),
                "p2_avg_regret": p2.average_regret(),
                "p1_l1_to_uniform": float(np.abs(p1_avg - uniform).sum()),
                "p2_l1_to_uniform": float(np.abs(p2_avg - uniform).sum()),
            }

            for i, action_name in enumerate(ACTIONS):
                row[f"p1_avg_{action_name}"] = float(p1_avg[i])
                row[f"p2_avg_{action_name}"] = float(p2_avg[i])
                row[f"p1_regret_{action_name}"] = float(p1.regret_sum[i])
                row[f"p2_regret_{action_name}"] = float(p2.regret_sum[i])

            rows.append(row)

    return rows


def save_jsonl(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def save_csv(rows: list[dict], path: Path) -> pd.DataFrame:
    path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return df


def plot_average_strategy(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 5))

    for action_name in ACTIONS:
        ax.plot(
            df["iteration"],
            df[f"p1_avg_{action_name}"],
            label=f"P1 avg {action_name}",
        )

    ax.axhline(1.0 / 3.0, linestyle="--", label="Nash value = 1/3")
    ax.set_xscale("log")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Average strategy probability")
    ax.set_title("RPS Regret Matching: Average Strategy Convergence")
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def plot_average_regret(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 5))

    eps = 1e-12

    ax.plot(
        df["iteration"],
        df["p1_avg_regret"].clip(lower=eps),
        label="P1 average regret",
    )
    ax.plot(
        df["iteration"],
        df["p2_avg_regret"].clip(lower=eps),
        label="P2 average regret",
    )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Average regret R_T / T")
    ax.set_title("RPS Regret Matching: Average Regret Decay")
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--log-every", type=int, default=100)
    parser.add_argument("--out-dir", type=str, default="results")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)

    rows = run_self_play(
        iterations=args.iterations,
        seed=args.seed,
        log_every=args.log_every,
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    log_path = out_dir / "logs" / f"exp02_rps_convergence_{timestamp}_seed{args.seed}.jsonl"
    csv_path = out_dir / "tables" / f"exp02_rps_convergence_seed{args.seed}.csv"
    strategy_fig_path = out_dir / "figures" / f"week02_rps_average_strategy_seed{args.seed}.png"
    regret_fig_path = out_dir / "figures" / f"week02_rps_average_regret_seed{args.seed}.png"

    save_jsonl(rows, log_path)
    df = save_csv(rows, csv_path)

    plot_average_strategy(df, strategy_fig_path)
    plot_average_regret(df, regret_fig_path)

    final = df.iloc[-1]

    p1_final = np.array(
        [
            final["p1_avg_rock"],
            final["p1_avg_paper"],
            final["p1_avg_scissors"],
        ]
    )

    p2_final = np.array(
        [
            final["p2_avg_rock"],
            final["p2_avg_paper"],
            final["p2_avg_scissors"],
        ]
    )

    print("Experiment complete.")
    print(f"Iterations: {args.iterations}")
    print(f"Seed: {args.seed}")
    print(f"P1 final average strategy: {np.round(p1_final, 4)}")
    print(f"P2 final average strategy: {np.round(p2_final, 4)}")
    print(f"P1 final average regret: {final['p1_avg_regret']:.6f}")
    print(f"P2 final average regret: {final['p2_avg_regret']:.6f}")
    print(f"Saved CSV: {csv_path}")
    print(f"Saved JSONL log: {log_path}")
    print(f"Saved strategy plot: {strategy_fig_path}")
    print(f"Saved regret plot: {regret_fig_path}")


if __name__ == "__main__":
    main()