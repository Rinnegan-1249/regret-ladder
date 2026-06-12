from __future__ import annotations

import argparse

import pyspiel
from open_spiel.python.algorithms import cfr as os_cfr
from open_spiel.python.algorithms import exploitability

from poker_ai.agents.cfr import VanillaCFR


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", default="kuhn_poker")
    parser.add_argument("--iters", type=int, default=1_000)
    args = parser.parse_args()

    game = pyspiel.load_game(args.game)

    mine = VanillaCFR(game)
    ref = os_cfr.CFRSolver(game)
    for _ in range(args.iters):
        mine.step()
        ref.evaluate_and_update_policy()

    mine_exp = float(exploitability.exploitability(game, mine.average_policy()))
    ref_exp = float(exploitability.exploitability(game, ref.average_policy()))
    print(f"Game: {args.game}")
    print(f"Iterations: {args.iters}")
    print(f"Our VanillaCFR exploitability: {mine_exp:.8f}")
    print(f"OpenSpiel CFRSolver exploitability: {ref_exp:.8f}")
    print(f"Absolute difference: {abs(mine_exp - ref_exp):.8f}")

    print("\nSample learned average strategies from our CFR:")
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
