"""Week 6: round-robin tournament of all agents on Leduc Poker.

Trains VanillaCFR and CFRPlus on Leduc, then plays a 7-agent round-robin
against the 5 baseline agents using duplicate-pair evaluation. Mirrors the
Week 3 tournament (exp03_week3_tournament.py) but on the larger Leduc game.

Agents:
  Random, AlwaysFold, AlwaysCall, RuleBased, EVHeuristic,
  MineCFR<N>, MineCFRPlus<N>
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pyspiel

from poker_ai.agents.baselines import (
    AlwaysCallAgent,
    AlwaysFoldAgent,
    EVHeuristicAgent,
    RandomAgent,
    RuleBasedAgent,
)
from poker_ai.agents.cfr import PolicyAgent, VanillaCFR
from poker_ai.agents.cfr_plus import CFRPlus
from poker_ai.evaluation.tournament import (
    add_average_and_max,
    run_round_robin,
    save_paper_style_table,
)


def build_agents(game, cfr_iters: int):
    print(f"Training VanillaCFR for {cfr_iters} iterations on Leduc Poker...")
    mine_cfr = VanillaCFR(game).train(cfr_iters)
    cfr_agent = PolicyAgent(
        game, mine_cfr.average_policy(), name=f"CFR{cfr_iters}"
    )

    print(f"Training CFRPlus for {cfr_iters} iterations on Leduc Poker...")
    mine_cfrp = CFRPlus(game).train(cfr_iters)
    cfrp_agent = PolicyAgent(
        game, mine_cfrp.average_policy(), name=f"CFRPlus{cfr_iters}"
    )

    return [
        RandomAgent(),
        AlwaysFoldAgent(),
        AlwaysCallAgent(),
        RuleBasedAgent(),
        EVHeuristicAgent(),
        cfr_agent,
        cfrp_agent,
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Week 6: 7-agent round-robin tournament on Leduc Poker."
    )
    parser.add_argument("--game", default="leduc_poker")
    parser.add_argument("--cfr-iters", type=int, default=5_000,
                        help="CFR/CFR+ training iterations; 5k ~ 12 min on Leduc")
    parser.add_argument("--n-pairs", type=int, default=5_000,
                        help="duplicate pairs per seed")
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2, 3, 4])
    parser.add_argument("--outdir", default="results")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    (outdir / "tables").mkdir(parents=True, exist_ok=True)
    (outdir / "figures").mkdir(parents=True, exist_ok=True)

    game = pyspiel.load_game(args.game)
    agents = build_agents(game, args.cfr_iters)

    print(f"\nRunning round-robin: {len(agents)} agents, "
          f"{args.n_pairs} pairs/seed, seeds={args.seeds}...")
    matrix, long_df = run_round_robin(
        game, agents, n_pairs=args.n_pairs, seeds=args.seeds
    )
    matrix_with_avg = add_average_and_max(matrix)

    matrix_csv = outdir / "tables" / "week06_leduc_payoff_matrix.csv"
    long_csv   = outdir / "tables" / "week06_leduc_pairwise_with_ci.csv"
    png_path   = outdir / "figures" / "week06_leduc_payoff_matrix.png"

    matrix_with_avg.to_csv(matrix_csv)
    long_df.to_csv(long_csv, index=False)
    save_paper_style_table(
        matrix_with_avg,
        png_path,
        title=(
            f"Week 6 Leduc Poker cross-table: row-player payoff (chips/hand); "
            f"{args.n_pairs} duplicate pairs/seed, CFR iters={args.cfr_iters}"
        ),
    )

    print("\nPayoff matrix, row-player chips/hand:")
    print(matrix_with_avg.round(4).to_string())
    print(f"\nSaved {matrix_csv}")
    print(f"Saved {long_csv}")
    print(f"Saved {png_path}")


if __name__ == "__main__":
    main()
