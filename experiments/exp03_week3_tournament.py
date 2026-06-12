from __future__ import annotations

import argparse
from pathlib import Path

import pyspiel
from open_spiel.python.algorithms import cfr as os_cfr

from poker_ai.agents.baselines import (
    RandomAgent,
    AlwaysFoldAgent,
    AlwaysCallAgent,
    RuleBasedAgent,
    EVHeuristicAgent,
)
from poker_ai.agents.cfr import PolicyAgent, VanillaCFR
from poker_ai.evaluation.tournament import add_average_and_max, run_round_robin, save_paper_style_table


def build_agents(game, cfr_iters: int):
    print(f"Training our VanillaCFR for {cfr_iters} iterations...")
    mine = VanillaCFR(game).train(cfr_iters)
    mine_agent = PolicyAgent(game, mine.average_policy(), name=f"MineCFR{cfr_iters}")

    print(f"Training OpenSpiel CFRSolver for {cfr_iters} iterations...")
    ref = os_cfr.CFRSolver(game)
    for _ in range(cfr_iters):
        ref.evaluate_and_update_policy()
    ref_agent = PolicyAgent(game, ref.average_policy(), name=f"OpenSpielCFR{cfr_iters}")

    return [
        RandomAgent(),
        AlwaysFoldAgent(),
        AlwaysCallAgent(),
        RuleBasedAgent(),
        EVHeuristicAgent(),
        mine_agent,
        ref_agent,
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", default="kuhn_poker")
    parser.add_argument("--cfr-iters", type=int, default=10_000)
    parser.add_argument("--n-pairs", type=int, default=10_000, help="duplicate pairs per seed")
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2, 3, 4])
    parser.add_argument("--outdir", default="results")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    (outdir / "tables").mkdir(parents=True, exist_ok=True)
    (outdir / "figures").mkdir(parents=True, exist_ok=True)

    game = pyspiel.load_game(args.game)
    agents = build_agents(game, args.cfr_iters)
    matrix, long_df = run_round_robin(game, agents, n_pairs=args.n_pairs, seeds=args.seeds)
    matrix_with_avg = add_average_and_max(matrix)

    matrix_csv = outdir / "tables" / "week03_payoff_matrix.csv"
    long_csv = outdir / "tables" / "week03_pairwise_with_ci.csv"
    png_path = outdir / "figures" / "week03_payoff_matrix.png"

    matrix_with_avg.to_csv(matrix_csv)
    long_df.to_csv(long_csv, index=False)
    save_paper_style_table(
        matrix_with_avg,
        png_path,
        title=f"Week 3 Kuhn Poker cross-table: row-player payoff, chips/hand; {args.n_pairs} duplicate pairs/seed",
    )

    print("\nPayoff matrix, row-player chips/hand:")
    print(matrix_with_avg.round(4).to_string())
    print(f"\nSaved {matrix_csv}")
    print(f"Saved {long_csv}")
    print(f"Saved {png_path}")


if __name__ == "__main__":
    main()
