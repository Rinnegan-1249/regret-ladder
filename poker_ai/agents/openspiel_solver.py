"""Thin wrapper around OpenSpiel's built-in CFR solver."""
from __future__ import annotations

from open_spiel.python.algorithms import cfr

from poker_ai.agents.cfr import PolicyAgent


def train_openspiel_cfr_agent(game, iterations: int, name: str | None = None) -> PolicyAgent:
    solver = cfr.CFRSolver(game)
    for _ in range(iterations):
        solver.evaluate_and_update_policy()
    return PolicyAgent(game=game, policy=solver.average_policy(), name=name or f"OpenSpielCFR{iterations}")
