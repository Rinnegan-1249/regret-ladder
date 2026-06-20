"""Validate our OS-MCCFR and ES-MCCFR against OpenSpiel's reference solvers on Leduc Poker.

MCCFR is stochastic, so traces cannot match exactly. This checks that our
solvers converge at the same order of magnitude as OpenSpiel's implementations
at matching iteration counts.
"""
from __future__ import annotations

import argparse

import pyspiel
from open_spiel.python.algorithms import exploitability
from open_spiel.python.algorithms import external_sampling_mccfr as os_es
from open_spiel.python.algorithms import outcome_sampling_mccfr as os_os

from poker_ai.agents.mccfr_external import ExternalSamplingMCCFR
from poker_ai.agents.mccfr_outcome import OutcomeSamplingMCCFR


def expl(game, policy) -> float:
    return float(exploitability.exploitability(game, policy))


def main():
    parser = argparse.ArgumentParser(
        description="Validate OS/ES-MCCFR on Leduc Poker vs OpenSpiel."
    )
    parser.add_argument("--game", default="leduc_poker")
    parser.add_argument("--os-iters", type=int, default=100_000)
    parser.add_argument("--es-iters", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    game = pyspiel.load_game(args.game)

    print(f"Game: {args.game}  seed: {args.seed}\n")

    print(f"{'=== Outcome Sampling MCCFR, ' + str(args.os_iters) + ' iterations':=<60}")
    ours_os = OutcomeSamplingMCCFR(game, seed=args.seed)
    ref_os = os_os.OutcomeSamplingSolver(game)
    checkpoints = sorted({args.os_iters // 100, args.os_iters // 10, args.os_iters})
    for t in range(1, args.os_iters + 1):
        ours_os.step()
        ref_os.iteration()
        if t in checkpoints:
            m = expl(game, ours_os.average_policy())
            r = expl(game, ref_os.average_policy())
            print(f"iter={t:8d}  ours={m:.6f}  openspiel={r:.6f}")

    print()

    print(f"{'=== External Sampling MCCFR, ' + str(args.es_iters) + ' iterations':=<60}")
    ours_es = ExternalSamplingMCCFR(game, seed=args.seed)
    ref_es = os_es.ExternalSamplingSolver(game)
    checkpoints = sorted({args.es_iters // 100, args.es_iters // 10, args.es_iters})
    for t in range(1, args.es_iters + 1):
        ours_es.step()
        ref_es.iteration()
        if t in checkpoints:
            m = expl(game, ours_es.average_policy())
            r = expl(game, ref_es.average_policy())
            print(f"iter={t:8d}  ours={m:.6f}  openspiel={r:.6f}")


if __name__ == "__main__":
    main()
