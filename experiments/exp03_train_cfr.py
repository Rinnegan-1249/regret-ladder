from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pyspiel
from open_spiel.python.algorithms import cfr as os_cfr
from open_spiel.python.algorithms import exploitability

from poker_ai.agents.cfr import VanillaCFR


def log_points(max_iter: int) -> set[int]:
    pts = {1, 2, 5, 10, 20, 50, 100}
    x = 200
    while x <= max_iter:
        pts.add(x)
        x += 200 if x < 2000 else 1000
    pts.add(max_iter)
    return {p for p in pts if 1 <= p <= max_iter}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", default="kuhn_poker")
    parser.add_argument("--iters", type=int, default=10_000)
    parser.add_argument("--outdir", default="results")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    (outdir / "tables").mkdir(parents=True, exist_ok=True)
    (outdir / "figures").mkdir(parents=True, exist_ok=True)

    game = pyspiel.load_game(args.game)
    mine = VanillaCFR(game)
    ref = os_cfr.CFRSolver(game)
    pts = log_points(args.iters)

    rows = []
    for t in range(1, args.iters + 1):
        mine.step()
        ref.evaluate_and_update_policy()
        if t in pts:
            mine_exp = float(exploitability.exploitability(game, mine.average_policy()))
            ref_exp = float(exploitability.exploitability(game, ref.average_policy()))
            print(f"iter={t:6d}  mine={mine_exp:.8f}  openspiel={ref_exp:.8f}")
            rows.append({"iteration": t, "solver": "Mine_VanillaCFR", "exploitability": mine_exp})
            rows.append({"iteration": t, "solver": "OpenSpiel_CFRSolver", "exploitability": ref_exp})

    df = pd.DataFrame(rows)
    csv_path = outdir / "tables" / "week03_cfr_convergence.csv"
    df.to_csv(csv_path, index=False)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    for solver, sub in df.groupby("solver"):
        ax.loglog(sub["iteration"], sub["exploitability"], marker="o", label=solver)
    ax.set_xlabel("CFR iterations")
    ax.set_ylabel("Exploitability")
    ax.set_title(f"Week 3: Vanilla CFR convergence on {args.game}")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig_path = outdir / "figures" / "week03_cfr_convergence.png"
    fig.savefig(fig_path, dpi=200)
    print(f"Saved {csv_path}")
    print(f"Saved {fig_path}")


if __name__ == "__main__":
    main()
