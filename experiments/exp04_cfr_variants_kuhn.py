"""Week 4 experiment: vanilla CFR vs CFR+ on Kuhn Poker.

Trains both solvers side by side and, at log-spaced checkpoints, records:

- exploitability of the AVERAGE strategy of each solver,
- exploitability of the CURRENT strategy of each solver
  (the paper's claim: CFR+'s current profile (nearly) converges to Nash
  directly, while CFR's current profile does not),
- cumulative training wall-clock seconds (per-second comparison),
- fraction of (infoset, legal action) regret entries that are exactly zero
  (CFR+ compressibility property, Tammelin 2014 section 3),
- game value of each average profile (Kuhn Nash value for player 0
  is -1/18),
- current-strategy bet probabilities at player 0's opening infosets
  (J="0", Q="1", K="2") to visualize convergence to the Kuhn Nash family:
  bet(J)=alpha, bet(Q)=0, bet(K)=3*alpha with alpha in [0, 1/3].
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyspiel
from open_spiel.python.algorithms import expected_game_score

from poker_ai.agents.cfr import VanillaCFR
from poker_ai.agents.cfr_plus import CFRPlus
from poker_ai.evaluation.exploitability import compute_exploitability

KUHN_VALUE_P0 = -1.0 / 18.0
OPENING_INFOSTATES = {"J": "0", "Q": "1", "K": "2"}
BET_ACTION = 1


def log_points(max_iter: int) -> set[int]:
    pts = {1, 2, 5, 10, 20, 50, 100}
    x = 200
    while x <= max_iter:
        pts.add(x)
        x += 200 if x < 2000 else 1000
    pts.add(max_iter)
    return {p for p in pts if 1 <= p <= max_iter}


def zero_regret_fraction(solver) -> float:
    """Fraction of (infoset, legal action) regret entries that are exactly 0."""
    total = 0
    zeros = 0
    for info_state, legal_actions in solver.legal_actions_by_info_state.items():
        for a in legal_actions:
            total += 1
            if solver.regret_sum[info_state][a] == 0.0:
                zeros += 1
    return zeros / total if total else float("nan")


def bet_prob(tabular_policy, info_state: str) -> float:
    """P(bet) at a given information state of a TabularPolicy."""
    try:
        return float(tabular_policy.policy_for_key(info_state)[BET_ACTION])
    except (KeyError, LookupError):
        return float("nan")


def profile_value_p0(game, tabular_policy) -> float:
    """Expected value for player 0 when both players follow the policy."""
    values = expected_game_score.policy_value(
        game.new_initial_state(), [tabular_policy, tabular_policy]
    )
    return float(values[0])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", default="kuhn_poker")
    parser.add_argument("--iters", type=int, default=10_000)
    parser.add_argument("--delay", type=int, default=0, help="CFR+ averaging delay d")
    parser.add_argument("--outdir", default="results")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    (outdir / "tables").mkdir(parents=True, exist_ok=True)
    (outdir / "figures").mkdir(parents=True, exist_ok=True)

    game = pyspiel.load_game(args.game)
    cfr = VanillaCFR(game)
    cfrp = CFRPlus(game, delay=args.delay)
    pts = log_points(args.iters)

    cfr_seconds = 0.0
    cfrp_seconds = 0.0
    rows = []

    for t in range(1, args.iters + 1):
        t0 = time.perf_counter()
        cfr.step()
        t1 = time.perf_counter()
        cfrp.step()
        t2 = time.perf_counter()
        cfr_seconds += t1 - t0
        cfrp_seconds += t2 - t1

        if t in pts:
            cfr_avg = cfr.average_policy()
            cfr_cur = cfr.current_policy()
            cfrp_avg = cfrp.average_policy()
            cfrp_cur = cfrp.current_policy()

            row = {
                "iteration": t,
                "cfr_avg_expl": compute_exploitability(game, cfr_avg),
                "cfr_cur_expl": compute_exploitability(game, cfr_cur),
                "cfrplus_avg_expl": compute_exploitability(game, cfrp_avg),
                "cfrplus_cur_expl": compute_exploitability(game, cfrp_cur),
                "cfr_seconds": cfr_seconds,
                "cfrplus_seconds": cfrp_seconds,
                "cfr_zero_regret_frac": zero_regret_fraction(cfr),
                "cfrplus_zero_regret_frac": zero_regret_fraction(cfrp),
                "cfr_avg_value_p0": profile_value_p0(game, cfr_avg),
                "cfrplus_avg_value_p0": profile_value_p0(game, cfrp_avg),
            }
            for card, info_state in OPENING_INFOSTATES.items():
                row[f"cfr_cur_bet_{card}"] = bet_prob(cfr_cur, info_state)
                row[f"cfrplus_cur_bet_{card}"] = bet_prob(cfrp_cur, info_state)
            rows.append(row)

            print(
                f"iter={t:6d}  "
                f"CFR avg={row['cfr_avg_expl']:.2e} cur={row['cfr_cur_expl']:.2e}  "
                f"CFR+ avg={row['cfrplus_avg_expl']:.2e} cur={row['cfrplus_cur_expl']:.2e}"
            )

    df = pd.DataFrame(rows).sort_values("iteration")
    csv_path = outdir / "tables" / "week04_cfr_vs_cfrplus.csv"
    df.to_csv(csv_path, index=False)
    print(f"Saved {csv_path}")

    eps = 1e-12
    curves = [
        ("cfr_avg_expl", "CFR average strategy", "tab:red", "-"),
        ("cfr_cur_expl", "CFR current strategy", "tab:red", ":"),
        ("cfrplus_avg_expl", "CFR+ average strategy", "tab:green", "-"),
        ("cfrplus_cur_expl", "CFR+ current strategy", "tab:blue", ":"),
    ]

    # 1. Exploitability vs iterations (headline plot).
    fig, ax = plt.subplots(figsize=(8, 5))
    for col, label, color, ls in curves:
        ax.loglog(df["iteration"], df[col].clip(lower=eps), color=color, linestyle=ls, label=label)
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Exploitability")
    ax.set_title(f"Week 4: CFR vs CFR+ on {args.game} (delay d={args.delay})")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    p = outdir / "figures" / "week04_exploitability_vs_iterations.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    print(f"Saved {p}")

    # 2. Exploitability vs wall-clock seconds.
    fig, ax = plt.subplots(figsize=(8, 5))
    for col, label, color, ls in curves:
        seconds = df["cfr_seconds"] if col.startswith("cfr_") else df["cfrplus_seconds"]
        ax.loglog(seconds, df[col].clip(lower=eps), color=color, linestyle=ls, label=label)
    ax.set_xlabel("Training wall-clock seconds")
    ax.set_ylabel("Exploitability")
    ax.set_title(f"Week 4: CFR vs CFR+ on {args.game}, per-second comparison")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    p = outdir / "figures" / "week04_exploitability_vs_time.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    print(f"Saved {p}")

    # 3. Zero-regret fraction (compressibility, paper section 3).
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.semilogx(df["iteration"], df["cfr_zero_regret_frac"], color="tab:red", label="CFR")
    ax.semilogx(df["iteration"], df["cfrplus_zero_regret_frac"], color="tab:green", label="CFR+")
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Fraction of regret entries exactly 0")
    ax.set_title("Week 4: zero cumulative regrets (CFR+ compressibility property)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    p = outdir / "figures" / "week04_zero_regret_fraction.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    print(f"Saved {p}")

    # 4. Current-strategy convergence at player 0's opening infosets.
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = {"J": "tab:blue", "Q": "tab:orange", "K": "tab:green"}
    for card in OPENING_INFOSTATES:
        ax.semilogx(
            df["iteration"], df[f"cfrplus_cur_bet_{card}"],
            color=colors[card], linestyle="-", label=f"CFR+ current: bet with {card}",
        )
        ax.semilogx(
            df["iteration"], df[f"cfr_cur_bet_{card}"],
            color=colors[card], linestyle=":", alpha=0.6, label=f"CFR current: bet with {card}",
        )
    ax.set_xlabel("Iteration")
    ax.set_ylabel("P(bet) at player 0's opening decision")
    ax.set_title("Week 4: current strategy convergence to the Kuhn Nash family")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    p = outdir / "figures" / "week04_current_strategy_trace.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    print(f"Saved {p}")

    # Nash family consistency check on the final CFR+ average strategy:
    # bet(J) = alpha, bet(Q) = 0, bet(K) = 3*alpha, alpha in [0, 1/3].
    final_avg = cfrp.average_policy()
    alpha = bet_prob(final_avg, OPENING_INFOSTATES["J"])
    bet_q = bet_prob(final_avg, OPENING_INFOSTATES["Q"])
    bet_k = bet_prob(final_avg, OPENING_INFOSTATES["K"])
    final = df.iloc[-1]

    print("\n=== Final summary ===")
    print(f"CFR   average-strategy exploitability: {final['cfr_avg_expl']:.3e}")
    print(f"CFR+  average-strategy exploitability: {final['cfrplus_avg_expl']:.3e}")
    print(f"CFR   current-strategy exploitability: {final['cfr_cur_expl']:.3e}")
    print(f"CFR+  current-strategy exploitability: {final['cfrplus_cur_expl']:.3e}")
    print(f"CFR+  game value (player 0): {final['cfrplus_avg_value_p0']:.6f} "
          f"(Kuhn Nash value: {KUHN_VALUE_P0:.6f})")
    print("\nKuhn Nash family check on CFR+ average strategy "
          "(bet J = alpha, bet Q = 0, bet K = 3*alpha):")
    print(f"  alpha = P(bet|J) = {alpha:.4f}  (must be in [0, 1/3])")
    print(f"  P(bet|Q) = {bet_q:.4f}  (Nash: 0)")
    print(f"  P(bet|K) = {bet_k:.4f}  vs 3*alpha = {3 * alpha:.4f}")


if __name__ == "__main__":
    main()
