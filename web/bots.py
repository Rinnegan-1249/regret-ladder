"""Bot registry for the website.

CFR-family Kuhn bots are frozen AVERAGE policies trained with the project's
actual solvers and cached as JSON under web/cache/ (gitignored; regenerated
on first use). Baseline bots are the existing Week 1 agent classes. The RPS
bot is the average strategy of 10^4 expected-update regret-matching
self-play iterations (exactly the exp02 setup).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pyspiel

from poker_ai.agents.always_call import AlwaysCallAgent
from poker_ai.agents.always_fold import AlwaysFoldAgent
from poker_ai.agents.ev_heuristic import EVHeuristicAgent
from poker_ai.agents.random_agent import RandomAgent
from poker_ai.agents.regret_matching import RegretMatchingAgent
from poker_ai.agents.rule_based import RuleBasedAgent
from poker_ai.env.rps import PAYOFF_MATRIX

CACHE_DIR = Path(__file__).parent / "cache"

# bot_id -> (label, solver factory name, iterations, seed-or-None)
KUHN_CFR_BOTS = {
    "cfr": ("Vanilla CFR (10k iters)", "cfr", 10_000, None),
    "cfr_plus": ("CFR+ (10k iters)", "cfr_plus", 10_000, None),
    "os_mccfr": ("OS-MCCFR (100k iters, seed 0)", "os_mccfr", 100_000, 0),
    "es_mccfr": ("ES-MCCFR (50k iters, seed 0)", "es_mccfr", 50_000, 0),
}

KUHN_BASELINE_BOTS = {
    "random": ("Random", lambda seed: RandomAgent(seed=seed)),
    "always_call": ("Always-Call", lambda seed: AlwaysCallAgent()),
    "always_fold": ("Always-Fold", lambda seed: AlwaysFoldAgent()),
    "rule_based": ("Rule-Based", lambda seed: RuleBasedAgent()),
    "ev_heuristic": ("EV-Heuristic", lambda seed: EVHeuristicAgent(seed=seed)),
}

RPS_TRAIN_ITERS = 10_000


def _train_kuhn_solver(kind: str, iterations: int, seed: int | None):
    game = pyspiel.load_game("kuhn_poker")
    if kind == "cfr":
        from poker_ai.agents.cfr import VanillaCFR
        solver = VanillaCFR(game)
    elif kind == "cfr_plus":
        from poker_ai.agents.cfr_plus import CFRPlus
        solver = CFRPlus(game)
    elif kind == "os_mccfr":
        from poker_ai.agents.mccfr_outcome import OutcomeSamplingMCCFR
        solver = OutcomeSamplingMCCFR(game, seed=seed)
    elif kind == "es_mccfr":
        from poker_ai.agents.mccfr_external import ExternalSamplingMCCFR
        solver = ExternalSamplingMCCFR(game, seed=seed)
    else:
        raise ValueError(f"Unknown solver kind {kind}")
    solver.train(iterations)
    return solver


def _solver_average_table(solver) -> dict[str, list[float]]:
    """info_state -> normalized average-strategy probs (full action vector)."""
    table = {}
    for info_state, legal in solver.legal_actions_by_info_state.items():
        probs = np.zeros(solver.num_actions, dtype=np.float64)
        normalizer = sum(solver.strategy_sum[info_state][a] for a in legal)
        if normalizer > 0:
            for a in legal:
                probs[a] = solver.strategy_sum[info_state][a] / normalizer
        else:
            for a in legal:
                probs[a] = 1.0 / len(legal)
        table[info_state] = [float(p) for p in probs]
    return table


def get_kuhn_policy_table(bot_id: str) -> dict[str, list[float]]:
    """Cached frozen average policy for a CFR-family bot."""
    label, kind, iterations, seed = KUHN_CFR_BOTS[bot_id]
    cache = CACHE_DIR / f"kuhn_{bot_id}_{iterations}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    solver = _train_kuhn_solver(kind, iterations, seed)
    table = _solver_average_table(solver)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(table), encoding="utf-8")
    return table


class TablePolicyBot:
    """Plays a frozen info_state -> probs table (Kuhn CFR-family bots)."""

    def __init__(self, name: str, table: dict[str, list[float]], seed: int | None = None):
        self.name = name
        self.table = table
        self.rng = np.random.default_rng(seed)

    def act(self, state) -> int:
        player = state.current_player()
        info_state = state.information_state_string(player)
        legal = list(state.legal_actions())
        probs = self.table.get(info_state)
        if probs is None:
            weights = np.ones(len(legal)) / len(legal)
        else:
            weights = np.array([probs[a] for a in legal], dtype=np.float64)
            total = weights.sum()
            weights = weights / total if total > 0 else np.ones(len(legal)) / len(legal)
        return int(self.rng.choice(legal, p=weights))


def make_kuhn_bot(bot_id: str, seed: int = 0):
    if bot_id in KUHN_BASELINE_BOTS:
        label, factory = KUHN_BASELINE_BOTS[bot_id]
        agent = factory(seed)
        agent.name = label
        return agent
    if bot_id in KUHN_CFR_BOTS:
        label = KUHN_CFR_BOTS[bot_id][0]
        return TablePolicyBot(label, get_kuhn_policy_table(bot_id), seed=seed)
    raise ValueError(f"Unknown Kuhn bot id: {bot_id}")


def get_rps_frozen_strategy() -> list[float]:
    """Average strategy after 10^4 expected-update RM self-play iterations
    (the exp02 setup), cached."""
    cache = CACHE_DIR / f"rps_rm_{RPS_TRAIN_ITERS}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))

    p1 = RegretMatchingAgent(num_actions=3, seed=0)
    p2 = RegretMatchingAgent(num_actions=3, seed=10_000)
    # Same symmetry-breaking perturbation as exp02 (uniform is a fixed point
    # of the expected dynamics).
    p1.regret_sum[:] = p1.rng.uniform(0.0, 1.0, size=3)
    p2.regret_sum[:] = p2.rng.uniform(0.0, 1.0, size=3)
    for _ in range(RPS_TRAIN_ITERS):
        s1 = p1.current_strategy()
        s2 = p2.current_strategy()
        p1.update_expected(s1, PAYOFF_MATRIX @ s2)
        p2.update_expected(s2, PAYOFF_MATRIX @ s1)
    strategy = [float(x) for x in p1.average_strategy()]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(strategy), encoding="utf-8")
    return strategy


def list_kuhn_bots() -> list[dict]:
    bots = [{"id": bid, "label": label, "family": "baseline"}
            for bid, (label, _f) in KUHN_BASELINE_BOTS.items()]
    bots += [{"id": bid, "label": spec[0], "family": "cfr"}
             for bid, spec in KUHN_CFR_BOTS.items()]
    return bots
