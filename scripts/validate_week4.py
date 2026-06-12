"""Validate our CFR+ against OpenSpiel's CFRPlusSolver.

The two implementations may differ slightly in averaging details, so this
compares convergence (exploitability at checkpoints), not exact equality.
"""
from __future__ import annotations

import argparse

import pyspiel
from open_spiel.python.algorithms import cfr as os_cfr
from open_spiel.python.algorithms import exploitability

from poker_ai.agents.cfr_plus import CFRPlus


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", default="kuhn_poker")
    parser.add_argument("--iters", type=int, default=1_000)
    parser.add_argument("--delay", type=int, default=0)
    args = parser.parse_args()

    game = pyspiel.load_game(args.game)

    mine = CFRPlus(game, delay=args.delay)
    ref = os_cfr.CFRPlusSolver(game)

    checkpoints = sorted({10, 100, args.iters // 2, args.iters} & set(range(1, args.iters + 1)))
    print(f"Game: {args.game}, iterations: {args.iters}, delay: {args.delay}\n")

    for t in range(1, args.iters + 1):
        mine.step()
        ref.evaluate_and_update_policy()
        if t in checkpoints:
            mine_exp = float(exploitability.exploitability(game, mine.average_policy()))
            ref_exp = float(exploitability.exploitability(game, ref.average_policy()))
            print(f"iter={t:6d}  ours={mine_exp:.8f}  openspiel={ref_exp:.8f}")

    print("\nSample learned average strategies from our CFR+:")
    pol = mine.average_policy()
    shown = 0
    for info_state in sorted(mine.legal_actions_by_info_state):
        probs = pol.policy_for_key(info_state)
        legal = mine.legal_actions_by_info_state[info_state]
        print(info_state, {a: round(float(probs[a]), 4) for a in legal})
        shown += 1
        if shown >= 12:
            break


if __name__ == "__main__":
    main()
