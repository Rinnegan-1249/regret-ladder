"""Week 5: vanilla CFR vs CFR+ on Leduc Poker.

Trains both solvers side by side and records exploitability at log-spaced
checkpoints. Leduc Poker has ~936 information states (vs 12 for Kuhn), so
convergence is slower per iteration; we run 100k iterations by default.

Three figures:
  1. Exploitability of average and current strategies vs iterations (log-log)
  2. Exploitability vs wall-clock seconds
  3. Fraction of regret entries exactly zero — CFR+'s compressibility advantage
     is even more pronounced on Leduc than on Kuhn (Tammelin 2014, section 3)
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
from poker_ai.evaluation.exploitability import compute_exploitability


def log_points(max_iter: int) -> set[int]:
    pts = {1, 2, 5, 10, 20, 50, 100, 200, 500}
    x = 1_000
    while x <= max_iter:
        pts.add(x)
        x += 1_000 if x < 10_000 else 5_000 if x < 50_000 else 10_000
    pts.add(max_iter)
    return {p for p in pts if 1 <= p <= max_iter}


def zero_regret_fraction(solver) -> float:
    total = zeros = 0
    for info_state, legal_actions in solver.legal_actions_by_info_state.items():
        for a in legal_actions:
            total += 1
            if solver.regret_sum[info_state][a] == 0.0:
                zeros += 1
    return zeros / total if total else float("nan")


def main():
    parser = argparse.ArgumentParser(
        description="Week 5: CFR vs CFR+ on Leduc Poker."
    )
    parser.add_argument("--game", default="leduc_poker")
    parser.add_argument("--iters", type=int, default=10_000,
                        help="iterations; 10k ~ 24 min on Leduc (0.145s/iter for CFR)")
    parser.add_argument("--delay", type=int, default=0, help="CFR+ averaging delay d")
    parser.add_argument("--outdir", default="results")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    (outdir / "tables").mkdir(parents=True, exist_ok=True)
    (outdir / "figures").mkdir(parents=True, exist_ok=True)

    game = pyspiel.load_game(args.game)
    cfr = VanillaCFR(game)
    cfrp = CFRPlus(game, delay=args.delay)

    # Warm up one step to populate legal_actions_by_info_state for both solvers
    cfr.step()
    cfrp.step()
    n_infosets_cfr = len(cfr.legal_actions_by_info_state)
    print(f"Game: {args.game}")
    print(f"  Infosets discovered after 1 step: {n_infosets_cfr} "
          f"(Kuhn Poker has 12 for reference)")
    print(f"  Iterations: {args.iters}  CFR+ delay: {args.delay}\n")

    pts = log_points(args.iters)
    cfr_seconds = 0.0
    cfrp_seconds = 0.0
    rows = []

    # Start from iteration 2 since we already ran step 1 above
    for t in range(2, args.iters + 1):
        t0 = time.perf_counter()
        cfr.step()
        t1 = time.perf_counter()
        cfrp.step()
        t2 = time.perf_counter()
        cfr_seconds += t1 - t0
        cfrp_seconds += t2 - t1

        if t in pts:
            cfr_avg_expl = compute_exploitability(game, cfr.average_policy())
            cfr_cur_expl = compute_exploitability(game, cfr.current_policy())
            cfrp_avg_expl = compute_exploitability(game, cfrp.average_policy())
            cfrp_cur_expl = compute_exploitability(game, cfrp.current_policy())

            rows.append({
                "iteration": t,
                "cfr_avg_expl": cfr_avg_expl,
                "cfr_cur_expl": cfr_cur_expl,
                "cfrplus_avg_expl": cfrp_avg_expl,
                "cfrplus_cur_expl": cfrp_cur_expl,
                "cfr_seconds": cfr_seconds,
                "cfrplus_seconds": cfrp_seconds,
                "cfr_zero_regret_frac": zero_regret_fraction(cfr),
                "cfrplus_zero_regret_frac": zero_regret_fraction(cfrp),
            })

            print(
                f"iter={t:7d}  "
                f"CFR avg={cfr_avg_expl:.3e} cur={cfr_cur_expl:.3e}  "
                f"CFR+ avg={cfrp_avg_expl:.3e} cur={cfrp_cur_expl:.3e}"
            )

    df = pd.DataFrame(rows).sort_values("iteration")
    csv_path = outdir / "tables" / "week05_leduc_cfr_variants.csv"
    df.to_csv(csv_path, index=False)
    print(f"\nSaved {csv_path}")

    eps = 1e-12
    curves = [
        ("cfr_avg_expl",    "CFR average strategy",  "tab:red",   "-"),
        ("cfr_cur_expl",    "CFR current strategy",  "tab:red",   ":"),
        ("cfrplus_avg_expl", "CFR+ average strategy", "tab:green", "-"),
        ("cfrplus_cur_expl", "CFR+ current strategy", "tab:blue",  ":"),
    ]

    # 1. Exploitability vs iterations
    fig, ax = plt.subplots(figsize=(8, 5))
    for col, label, color, ls in curves:
        ax.loglog(df["iteration"], df[col].clip(lower=eps),
                  color=color, linestyle=ls, label=label)
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Exploitability")
    ax.set_title(f"Week 5: CFR vs CFR+ on {args.game} (delay d={args.delay})")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    p = outdir / "figures" / "week05_exploitability_vs_iterations.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    print(f"Saved {p}")

    # 2. Exploitability vs wall-clock seconds
    fig, ax = plt.subplots(figsize=(8, 5))
    for col, label, color, ls in curves:
        seconds = df["cfr_seconds"] if col.startswith("cfr_") else df["cfrplus_seconds"]
        ax.loglog(seconds.clip(lower=1e-6), df[col].clip(lower=eps),
                  color=color, linestyle=ls, label=label)
    ax.set_xlabel("Training wall-clock seconds")
    ax.set_ylabel("Exploitability")
    ax.set_title(f"Week 5: CFR vs CFR+ on {args.game}, per-second comparison")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    p = outdir / "figures" / "week05_exploitability_vs_time.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    print(f"Saved {p}")

    # 3. Zero-regret fraction (compressibility)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.semilogx(df["iteration"], df["cfr_zero_regret_frac"],
                color="tab:red", label="CFR")
    ax.semilogx(df["iteration"], df["cfrplus_zero_regret_frac"],
                color="tab:green", label="CFR+")
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Fraction of regret entries exactly 0")
    ax.set_title("Week 5: zero cumulative regrets on Leduc Poker (compressibility)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    p = outdir / "figures" / "week05_zero_regret_fraction.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    print(f"Saved {p}")

    final = df.iloc[-1]
    print("\n=== Final summary ===")
    print(f"CFR   average-strategy exploitability: {final['cfr_avg_expl']:.3e}")
    print(f"CFR+  average-strategy exploitability: {final['cfrplus_avg_expl']:.3e}")
    print(f"CFR   current-strategy exploitability: {final['cfr_cur_expl']:.3e}")
    print(f"CFR+  current-strategy exploitability: {final['cfrplus_cur_expl']:.3e}")
    ratio = final["cfr_avg_expl"] / final["cfrplus_avg_expl"]
    print(f"Speed-up (CFR avg / CFR+ avg): {ratio:.1f}x")


if __name__ == "__main__":
    main()
