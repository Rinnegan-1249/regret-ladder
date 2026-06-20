"""Week 6: CFR family 4-way comparison on Leduc Poker.

Compares the average-strategy exploitability of:

    1. Vanilla CFR        (full tree traversal, simultaneous updates)
    2. CFR+               (full tree traversal, alternating + regret-matching+)
    3. OS-MCCFR           (outcome sampling, eps-greedy, one history per step)
    4. ES-MCCFR           (external sampling, enumerate update player's actions)

following Lanctot et al. (NIPS 2009). The headline plot is exploitability vs
NODES TOUCHED (implementation-independent), matching their Figure 1. We also
show per-iteration and per-second views.

Leduc Poker is ~78× larger than Kuhn in infoset count, making the per-node
advantage of sampling solvers more pronounced than on Kuhn.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyspiel

from poker_ai.agents.cfr import VanillaCFR
from poker_ai.agents.cfr_plus import CFRPlus
from poker_ai.agents.mccfr_external import ExternalSamplingMCCFR
from poker_ai.agents.mccfr_outcome import OutcomeSamplingMCCFR
from poker_ai.evaluation.exploitability import compute_exploitability


def log_points(max_iter: int, n: int = 30) -> list[int]:
    return sorted(np.unique(np.geomspace(1, max_iter, n).astype(int)))


def count_tree_nodes(game) -> int:
    """Total nodes in the game tree (terminal + chance + decision)."""
    def walk(state) -> int:
        n = 1
        if state.is_terminal():
            return n
        if state.is_chance_node():
            actions = [a for a, _ in state.chance_outcomes()]
        else:
            actions = state.legal_actions()
        for a in actions:
            child = state.clone()
            child.apply_action(int(a))
            n += walk(child)
        return n

    return walk(game.new_initial_state())


def run_full_traversal(game, solver, name: str, iters: int, nodes_per_iter: int) -> list[dict]:
    rows = []
    pts = set(log_points(iters))
    seconds = 0.0
    for t in range(1, iters + 1):
        t0 = time.perf_counter()
        solver.step()
        seconds += time.perf_counter() - t0
        if t in pts:
            rows.append({
                "algorithm": name,
                "seed": -1,
                "iteration": t,
                "nodes_touched": nodes_per_iter * t,
                "seconds": seconds,
                "exploitability": compute_exploitability(game, solver.average_policy()),
            })
    return rows


def run_mccfr(game, solver, name: str, seed: int, iters: int) -> list[dict]:
    rows = []
    pts = set(log_points(iters))
    seconds = 0.0
    for t in range(1, iters + 1):
        t0 = time.perf_counter()
        solver.step()
        seconds += time.perf_counter() - t0
        if t in pts:
            rows.append({
                "algorithm": name,
                "seed": seed,
                "iteration": t,
                "nodes_touched": solver.nodes_touched,
                "seconds": seconds,
                "exploitability": compute_exploitability(game, solver.average_policy()),
            })
    return rows


STYLE = {
    "CFR":      ("tab:red",    "Vanilla CFR"),
    "CFR+":     ("tab:green",  "CFR+"),
    "OS-MCCFR": ("tab:blue",   "OS-MCCFR"),
    "ES-MCCFR": ("tab:purple", "ES-MCCFR"),
}


def plot_overlay(df: pd.DataFrame, x_col: str, x_label: str, title: str, path: Path):
    eps = 1e-12
    fig, ax = plt.subplots(figsize=(8, 5))
    for algo, (color, label) in STYLE.items():
        sub = df[df["algorithm"] == algo]
        if sub.empty:
            continue
        seeds = sorted(sub["seed"].unique())
        if len(seeds) > 1:
            for s in seeds:
                ss = sub[sub["seed"] == s]
                ax.loglog(ss[x_col], ss["exploitability"].clip(lower=eps),
                          color=color, alpha=0.25, linewidth=0.8)
            mean = sub.groupby("iteration").mean(numeric_only=True).reset_index()
            ax.loglog(mean[x_col], mean["exploitability"].clip(lower=eps),
                      color=color, linewidth=2.0,
                      label=f"{label} (mean of {len(seeds)} seeds)")
        else:
            ax.loglog(sub[x_col], sub["exploitability"].clip(lower=eps),
                      color=color, linewidth=2.0, label=label)
    ax.set_xlabel(x_label)
    ax.set_ylabel("Exploitability of average strategy")
    ax.set_title(title)
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    print(f"Saved {path}")


def main():
    parser = argparse.ArgumentParser(
        description="Week 6: 4-way CFR comparison on Leduc Poker."
    )
    parser.add_argument("--game", default="leduc_poker")
    parser.add_argument("--iters", type=int, default=5_000,
                        help="CFR / CFR+ iterations; 5k ~ 12 min on Leduc")
    parser.add_argument("--os-iters", type=int, default=500_000,
                        help="OS-MCCFR iterations per seed; 500k ~ 6 min/seed on Leduc")
    parser.add_argument("--es-iters", type=int, default=100_000,
                        help="ES-MCCFR iterations per seed; 100k ~ 3 min/seed on Leduc")
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    parser.add_argument("--epsilon", type=float, default=0.6)
    parser.add_argument("--outdir", default="results")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    (outdir / "tables").mkdir(parents=True, exist_ok=True)
    (outdir / "figures").mkdir(parents=True, exist_ok=True)

    game = pyspiel.load_game(args.game)
    print(f"Counting tree nodes for {args.game} ...")
    n_nodes = count_tree_nodes(game)
    print(f"  {args.game}: {n_nodes} tree nodes; "
          f"CFR touches {n_nodes}/iter, CFR+ touches {2 * n_nodes}/iter\n")

    rows: list[dict] = []

    print(f"Training Vanilla CFR for {args.iters} iterations...")
    rows += run_full_traversal(game, VanillaCFR(game), "CFR", args.iters, n_nodes)

    print(f"Training CFR+ for {args.iters} iterations...")
    rows += run_full_traversal(game, CFRPlus(game), "CFR+", args.iters, 2 * n_nodes)

    for seed in args.seeds:
        print(f"Training OS-MCCFR (eps={args.epsilon}) seed={seed} "
              f"for {args.os_iters} iterations...")
        solver = OutcomeSamplingMCCFR(game, epsilon=args.epsilon, seed=seed)
        rows += run_mccfr(game, solver, "OS-MCCFR", seed, args.os_iters)

    for seed in args.seeds:
        print(f"Training ES-MCCFR seed={seed} for {args.es_iters} iterations...")
        solver = ExternalSamplingMCCFR(game, seed=seed)
        rows += run_mccfr(game, solver, "ES-MCCFR", seed, args.es_iters)

    df = pd.DataFrame(rows)
    csv_path = outdir / "tables" / "week06_leduc_mccfr.csv"
    df.to_csv(csv_path, index=False)
    print(f"\nSaved {csv_path}")

    game_tag = args.game
    plot_overlay(
        df, "nodes_touched", "Nodes touched",
        f"Week 6: CFR family on {game_tag} — paper-style comparison (Lanctot et al. Fig. 1)",
        outdir / "figures" / "week06_exploitability_vs_nodes.png",
    )
    plot_overlay(
        df, "iteration",
        "Iteration  (NOTE: per-iteration cost differs wildly across algorithms)",
        f"Week 6: CFR family on {game_tag} — per-iteration view",
        outdir / "figures" / "week06_exploitability_vs_iterations.png",
    )
    plot_overlay(
        df, "seconds", "Training wall-clock seconds",
        f"Week 6: CFR family on {game_tag} — per-second view",
        outdir / "figures" / "week06_exploitability_vs_time.png",
    )

    print("\n=== Final summary (each algorithm at its full budget) ===")
    for algo in STYLE:
        sub = df[df["algorithm"] == algo]
        if sub.empty:
            continue
        last = sub[sub["iteration"] == sub["iteration"].max()]
        expl = last["exploitability"].mean()
        nodes = last["nodes_touched"].mean()
        secs = last["seconds"].mean()
        n_seeds = len(last)
        seed_note = f" (mean of {n_seeds} seeds)" if n_seeds > 1 else ""
        print(f"{algo:10s} iters={sub['iteration'].max():>9d}  "
              f"exploitability={expl:.3e}{seed_note}  "
              f"nodes={nodes:.3g}  time={secs:.1f}s")


if __name__ == "__main__":
    main()
