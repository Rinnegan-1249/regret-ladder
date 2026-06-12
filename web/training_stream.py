"""Server-Sent-Events generators for live training graphs.

Each generator runs the project's actual solver loop and yields SSE events
(`data: <json>\\n\\n`) at ~log-spaced checkpoints, ending with a "done"
event. Hard iteration caps are enforced here.
"""
from __future__ import annotations

import json

import numpy as np
import pyspiel

from poker_ai.agents.regret_matching import RegretMatchingAgent
from poker_ai.env.rps import PAYOFF_MATRIX
from poker_ai.evaluation.exploitability import compute_exploitability

RPS_MAX_ITERS = 100_000
MAX_CHECKPOINTS = 150

# algo -> (solver factory, max iterations, takes seed)
KUHN_ALGOS = {
    "cfr": ("Vanilla CFR", 10_000, False),
    "cfr_plus": ("CFR+", 10_000, False),
    "os_mccfr": ("OS-MCCFR", 200_000, True),
    "es_mccfr": ("ES-MCCFR", 50_000, True),
}


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _checkpoints(iterations: int) -> set[int]:
    pts = np.unique(np.geomspace(1, iterations, MAX_CHECKPOINTS).astype(int))
    return set(int(p) for p in pts)


def rps_stream(iterations: int, seed: int):
    """Expected-update RM self-play (the exp02 setup), streamed."""
    iterations = max(1, min(int(iterations), RPS_MAX_ITERS))
    pts = _checkpoints(iterations)

    p1 = RegretMatchingAgent(num_actions=3, seed=seed)
    p2 = RegretMatchingAgent(num_actions=3, seed=seed + 10_000)
    # exp02's symmetry-breaking perturbation (uniform is a fixed point of
    # the expected dynamics).
    p1.regret_sum[:] = p1.rng.uniform(0.0, 1.0, size=3)
    p2.regret_sum[:] = p2.rng.uniform(0.0, 1.0, size=3)

    yield _sse({"type": "start", "iterations": iterations, "seed": seed})
    for t in range(1, iterations + 1):
        s1 = p1.current_strategy()
        s2 = p2.current_strategy()
        p1.update_expected(s1, PAYOFF_MATRIX @ s2)
        p2.update_expected(s2, PAYOFF_MATRIX @ s1)
        if t in pts:
            yield _sse({
                "type": "checkpoint",
                "t": t,
                "p1_avg": [float(x) for x in p1.average_strategy()],
                "p2_avg": [float(x) for x in p2.average_strategy()],
                "p1_avg_regret": p1.average_regret(),
                "p2_avg_regret": p2.average_regret(),
            })
    yield _sse({"type": "done"})


def _make_kuhn_solver(algo: str, game, seed: int):
    if algo == "cfr":
        from poker_ai.agents.cfr import VanillaCFR
        return VanillaCFR(game)
    if algo == "cfr_plus":
        from poker_ai.agents.cfr_plus import CFRPlus
        return CFRPlus(game)
    if algo == "os_mccfr":
        from poker_ai.agents.mccfr_outcome import OutcomeSamplingMCCFR
        return OutcomeSamplingMCCFR(game, seed=seed)
    if algo == "es_mccfr":
        from poker_ai.agents.mccfr_external import ExternalSamplingMCCFR
        return ExternalSamplingMCCFR(game, seed=seed)
    raise ValueError(f"Unknown algorithm: {algo}")


def _infoset_player(info_state: str) -> int:
    """In Kuhn, the info state string is <card><betting>; the acting player
    alternates with the betting length."""
    return len(info_state[1:]) % 2


def _avg_bet_probs(solver) -> dict[str, dict[str, float]]:
    """P(bet) of the average strategy at every infoset, split by player."""
    out = {"p1": {}, "p2": {}}
    for info_state, legal in solver.legal_actions_by_info_state.items():
        normalizer = sum(solver.strategy_sum[info_state][a] for a in legal)
        if normalizer > 0:
            p_bet = solver.strategy_sum[info_state][1] / normalizer
        else:
            p_bet = 1.0 / len(legal)
        out[f"p{_infoset_player(info_state) + 1}"][info_state] = float(p_bet)
    return out


def kuhn_stream(algo: str, iterations: int, seed: int):
    """Train the chosen solver, streaming average-strategy bet probabilities
    per infoset and exploitability at checkpoints."""
    if algo not in KUHN_ALGOS:
        yield _sse({"type": "error", "message": f"Unknown algorithm: {algo}"})
        return
    label, cap, _takes_seed = KUHN_ALGOS[algo]
    iterations = max(1, min(int(iterations), cap))
    pts = _checkpoints(iterations)

    game = pyspiel.load_game("kuhn_poker")
    solver = _make_kuhn_solver(algo, game, seed)

    yield _sse({"type": "start", "algo": algo, "label": label,
                "iterations": iterations, "seed": seed})
    for t in range(1, iterations + 1):
        solver.step()
        if t in pts:
            yield _sse({
                "type": "checkpoint",
                "t": t,
                "exploitability": compute_exploitability(game, solver.average_policy()),
                "bet_probs": _avg_bet_probs(solver),
            })
    yield _sse({"type": "done"})
