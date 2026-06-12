"""Validate our MCCFR solvers against OpenSpiel's reference implementations.

MCCFR is stochastic, so traces cannot match exactly; this checks that our
solvers converge at the same order of magnitude as OpenSpiel's
OutcomeSamplingSolver and ExternalSamplingSolver at matching iteration
counts.
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", default="kuhn_poker")
    parser.add_argument("--os-iters", type=int, default=100_000)
    parser.add_argument("--es-iters", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    game = pyspiel.load_game(args.game)

    print(f"--- Outcome sampling, {args.os_iters} iterations ---")
    ours = OutcomeSamplingMCCFR(game, seed=args.seed)
    ref = os_os.OutcomeSamplingSolver(game)
    checkpoints = sorted({args.os_iters // 100, args.os_iters // 10, args.os_iters})
    for t in range(1, args.os_iters + 1):
        ours.step()
        ref.iteration()
        if t in checkpoints:
            print(f"iter={t:7d}  ours={expl(game, ours.average_policy()):.6f}  "
                  f"openspiel={expl(game, ref.average_policy()):.6f}")

    print(f"\n--- External sampling, {args.es_iters} iterations ---")
    ours = ExternalSamplingMCCFR(game, seed=args.seed)
    ref = os_es.ExternalSamplingSolver(game)
    checkpoints = sorted({args.es_iters // 100, args.es_iters // 10, args.es_iters})
    for t in range(1, args.es_iters + 1):
        ours.step()
        ref.iteration()
        if t in checkpoints:
            print(f"iter={t:7d}  ours={expl(game, ours.average_policy()):.6f}  "
                  f"openspiel={expl(game, ref.average_policy()):.6f}")


if __name__ == "__main__":
    main()
