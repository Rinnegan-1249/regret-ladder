"""Validate our CFR and CFR+ against OpenSpiel's reference solvers on Leduc Poker.

Convergence traces are compared at log-spaced checkpoints. Expected behaviour:

- CFR+: ratio ours/OpenSpiel stays close to 1.0 — both use alternating updates.
- Vanilla CFR: ratio grows over iterations (~2.5x at 500 iters on Leduc). This is
  expected: OpenSpiel's CFRSolver uses alternating updates by default while ours
  uses simultaneous updates (Zinkevich 2007). Simultaneous CFR converges more slowly
  per iteration; the exploitability bound is the same up to a constant.
"""
from __future__ import annotations

import argparse

import pyspiel
from open_spiel.python.algorithms import cfr as os_cfr
from open_spiel.python.algorithms import exploitability

from poker_ai.agents.cfr import VanillaCFR
from poker_ai.agents.cfr_plus import CFRPlus


def expl(game, policy) -> float:
    return float(exploitability.exploitability(game, policy))


def main():
    parser = argparse.ArgumentParser(
        description="Validate CFR and CFR+ on Leduc Poker vs OpenSpiel."
    )
    parser.add_argument("--game", default="leduc_poker")
    parser.add_argument("--iters", type=int, default=10_000)
    parser.add_argument("--delay", type=int, default=0, help="CFR+ averaging delay")
    args = parser.parse_args()

    game = pyspiel.load_game(args.game)
    checkpoints = sorted(
        {10, 100, args.iters // 10, args.iters // 2, args.iters}
        & set(range(1, args.iters + 1))
    )

    print(f"Game: {args.game}  iterations: {args.iters}  delay: {args.delay}\n")

    # --- Vanilla CFR ---
    print(f"{'=== Vanilla CFR':=<60}")
    mine_cfr = VanillaCFR(game)
    ref_cfr = os_cfr.CFRSolver(game)
    for t in range(1, args.iters + 1):
        mine_cfr.step()
        ref_cfr.evaluate_and_update_policy()
        if t in checkpoints:
            m = expl(game, mine_cfr.average_policy())
            r = expl(game, ref_cfr.average_policy())
            print(f"iter={t:7d}  ours={m:.8f}  openspiel={r:.8f}  ratio={m/r:.3f}")

    print()

    # --- CFR+ ---
    print(f"{'=== CFR+ (delay=' + str(args.delay) + ')':=<60}")
    mine_cfrp = CFRPlus(game, delay=args.delay)
    ref_cfrp = os_cfr.CFRPlusSolver(game)
    for t in range(1, args.iters + 1):
        mine_cfrp.step()
        ref_cfrp.evaluate_and_update_policy()
        if t in checkpoints:
            m = expl(game, mine_cfrp.average_policy())
            r = expl(game, ref_cfrp.average_policy())
            print(f"iter={t:7d}  ours={m:.8f}  openspiel={r:.8f}  ratio={m/r:.3f}")

    print("\nSample learned strategies from our CFR+ average policy:")
    pol = mine_cfrp.average_policy()
    for i, info_state in enumerate(sorted(mine_cfrp.legal_actions_by_info_state)):
        probs = pol.policy_for_key(info_state)
        legal = mine_cfrp.legal_actions_by_info_state[info_state]
        print(f"  {info_state!r:20s}: {{{', '.join(f'{a}: {probs[a]:.4f}' for a in legal)}}}")
        if i >= 11:
            print("  ...")
            break


if __name__ == "__main__":
    main()
