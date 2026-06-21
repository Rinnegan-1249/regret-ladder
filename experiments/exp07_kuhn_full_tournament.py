"""Full Kuhn Poker round-robin: all 9 bots built across Weeks 1-4 together
(5 baselines + Vanilla CFR + CFR+ + OS-MCCFR + ES-MCCFR) - no prior
tournament had every one of these in the same cross-table at once.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pyspiel

from poker_ai.agents.baselines import (
    RandomAgent,
    AlwaysFoldAgent,
    AlwaysCallAgent,
    RuleBasedAgent,
    EVHeuristicAgent,
)
from poker_ai.agents.cfr import PolicyAgent, VanillaCFR
from poker_ai.agents.cfr_plus import CFRPlus
from poker_ai.agents.mccfr_outcome import OutcomeSamplingMCCFR
from poker_ai.agents.mccfr_external import ExternalSamplingMCCFR
from poker_ai.evaluation.tournament import add_average_and_max, run_round_robin, save_paper_style_table


def build_agents(game, cfr_iters: int, mccfr_seed: int):
    print(f"Training Vanilla CFR for {cfr_iters} iterations...")
    cfr = VanillaCFR(game).train(cfr_iters)
    cfr_agent = PolicyAgent(game, cfr.average_policy(), name=f"CFR{cfr_iters}")

    print(f"Training CFR+ for {cfr_iters} iterations...")
    cfr_plus = CFRPlus(game).train(cfr_iters)
    cfr_plus_agent = PolicyAgent(game, cfr_plus.average_policy(), name=f"CFR+{cfr_iters}")

    print(f"Training OS-MCCFR for {cfr_iters} iterations...")
    os_mccfr = OutcomeSamplingMCCFR(game, seed=mccfr_seed).train(cfr_iters)
    os_mccfr_agent = PolicyAgent(game, os_mccfr.average_policy(), name=f"OS-MCCFR{cfr_iters}")

    print(f"Training ES-MCCFR for {cfr_iters} iterations...")
    es_mccfr = ExternalSamplingMCCFR(game, seed=mccfr_seed).train(cfr_iters)
    es_mccfr_agent = PolicyAgent(game, es_mccfr.average_policy(), name=f"ES-MCCFR{cfr_iters}")

    return [
        RandomAgent(),
        AlwaysFoldAgent(),
        AlwaysCallAgent(),
        RuleBasedAgent(),
        EVHeuristicAgent(),
        cfr_agent,
        cfr_plus_agent,
        os_mccfr_agent,
        es_mccfr_agent,
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", default="kuhn_poker")
    parser.add_argument("--cfr-iters", type=int, default=10_000)
    parser.add_argument("--mccfr-seed", type=int, default=0)
    parser.add_argument("--n-pairs", type=int, default=10_000, help="duplicate pairs per seed")
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2, 3, 4])
    parser.add_argument("--outdir", default="results")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    (outdir / "tables").mkdir(parents=True, exist_ok=True)
    (outdir / "figures").mkdir(parents=True, exist_ok=True)

    game = pyspiel.load_game(args.game)
    agents = build_agents(game, args.cfr_iters, args.mccfr_seed)
    matrix, long_df = run_round_robin(game, agents, n_pairs=args.n_pairs, seeds=args.seeds)
    matrix_with_avg = add_average_and_max(matrix)

    matrix_csv = outdir / "tables" / "week07_kuhn_full_tournament_payoff_matrix.csv"
    long_csv = outdir / "tables" / "week07_kuhn_full_tournament_pairwise_with_ci.csv"
    png_path = outdir / "figures" / "week07_kuhn_full_tournament_payoff_matrix.png"

    matrix_with_avg.to_csv(matrix_csv)
    long_df.to_csv(long_csv, index=False)
    save_paper_style_table(
        matrix_with_avg,
        png_path,
        title=f"Full Kuhn Poker cross-table (9 agents): row-player payoff, chips/hand; {args.n_pairs} duplicate pairs/seed",
    )

    print("\nPayoff matrix, row-player chips/hand:")
    print(matrix_with_avg.round(4).to_string())
    print(f"\nSaved {matrix_csv}")
    print(f"Saved {long_csv}")
    print(f"Saved {png_path}")


if __name__ == "__main__":
    main()
