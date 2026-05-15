from __future__ import annotations
import pandas as pd
import argparse
from pathlib import Path

from poker_ai.agents.always_call import AlwaysCallAgent
from poker_ai.agents.always_fold import AlwaysFoldAgent
from poker_ai.agents.ev_heuristic import EVHeuristicAgent
from poker_ai.agents.random_agent import RandomAgent
from poker_ai.agents.rule_based import RuleBasedAgent
from poker_ai.evaluation.tournament import round_robin
from poker_ai.utils.seeding import seed_everything


def build_agents(seed: int):
    return {
        "random": RandomAgent(seed=10_000 + seed),
        "always_call": AlwaysCallAgent(),
        "always_fold": AlwaysFoldAgent(),
        "rule_based": RuleBasedAgent(),
        "ev_heuristic": EVHeuristicAgent(seed=20_000 + seed),
    }

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", default="kuhn_poker", choices=["kuhn_poker", "leduc_poker"])
    parser.add_argument("--n-pairs", type=int, default=10_000)
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    parser.add_argument("--out", default="results/tables/exp01_baseline_tournament.csv")
    args = parser.parse_args()

    all_dfs = []

    for seed in args.seeds:
        seed_everything(seed)

        agents = build_agents(seed=seed)

        df_seed = round_robin(
            game_name=args.game,
            agents=agents,
            n_pairs=args.n_pairs,
            seeds=[seed],
        )

        all_dfs.append(df_seed)

    df = pd.concat(all_dfs, ignore_index=True)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(df.to_string(index=False))
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
