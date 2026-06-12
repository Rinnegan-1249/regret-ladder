"""RPS match engine for the website.

Seat kinds:
    human         - picks an action each round (sent in the play request)
    distribution  - human-supplied mixed strategy; server samples each round
    rm_frozen     - frozen average strategy after 10^4 RM self-play iters
    rm_adaptive   - regret matching learning ONLINE from realized play only
                    (Hart & Mas-Colell 2000): after each round it updates its
                    regrets with the counterfactual utility vector against
                    the opponent's realized action.

Both committed actions are resolved server-side in a single request, so
neither side's choice is observable before the reveal.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

import numpy as np

from poker_ai.agents.regret_matching import RegretMatchingAgent
from poker_ai.env.rps import ACTIONS, action_utilities_against, payoff

from web.bots import get_rps_frozen_strategy

MAX_ROUNDS = 1_000
SEAT_KINDS = {"human", "distribution", "rm_frozen", "rm_adaptive"}


@dataclass
class SeatSpec:
    kind: str
    dist: list[float] | None = None  # only for kind == "distribution"

    def validate(self) -> None:
        if self.kind not in SEAT_KINDS:
            raise ValueError(f"Unknown seat kind: {self.kind}")
        if self.kind == "distribution":
            if self.dist is None or len(self.dist) != 3:
                raise ValueError("distribution seat needs a 3-vector dist")
            d = np.asarray(self.dist, dtype=np.float64)
            if np.any(d < 0) or not np.isclose(d.sum(), 1.0, atol=1e-6):
                raise ValueError("dist must be non-negative and sum to 1")


@dataclass
class RpsMatch:
    match_id: str
    seats: list[SeatSpec]
    rounds_total: int
    seed: int = 0
    created_at: float = field(default_factory=time.time)
    history: list[dict] = field(default_factory=list)
    scores: list[float] = field(default_factory=lambda: [0.0, 0.0])

    def __post_init__(self):
        self.rng = np.random.default_rng(self.seed)
        self.frozen_strategy = np.asarray(get_rps_frozen_strategy())
        self.adaptive: dict[int, RegretMatchingAgent] = {}
        for i, seat in enumerate(self.seats):
            if seat.kind == "rm_adaptive":
                self.adaptive[i] = RegretMatchingAgent(num_actions=3, seed=self.seed + i)

    @property
    def rounds_played(self) -> int:
        return len(self.history)

    @property
    def finished(self) -> bool:
        return self.rounds_played >= self.rounds_total

    def has_human(self) -> bool:
        return any(s.kind == "human" for s in self.seats)

    def _seat_action(self, i: int, human_action: int | None) -> tuple[int, np.ndarray | None]:
        """Returns (action, strategy_used_or_None) for seat i."""
        seat = self.seats[i]
        if seat.kind == "human":
            if human_action is None or human_action not in (0, 1, 2):
                raise ValueError(f"Player {i + 1} is human: an action in {{0,1,2}} is required")
            return human_action, None
        if seat.kind == "distribution":
            d = np.asarray(seat.dist, dtype=np.float64)
            d = d / d.sum()
            return int(self.rng.choice(3, p=d)), d
        if seat.kind == "rm_frozen":
            return int(self.rng.choice(3, p=self.frozen_strategy)), self.frozen_strategy
        # rm_adaptive
        agent = self.adaptive[i]
        strategy = agent.current_strategy()
        return int(agent.sample_action(strategy)), strategy

    def play_round(self, p1_action: int | None = None, p2_action: int | None = None) -> dict:
        if self.finished:
            raise ValueError("Match already finished")

        a1, s1 = self._seat_action(0, p1_action)
        a2, s2 = self._seat_action(1, p2_action)

        u1 = payoff(a1, a2)
        self.scores[0] += u1
        self.scores[1] -= u1

        # Hart & Mas-Colell update: each adaptive agent uses ONLY the
        # opponent's realized action (the counterfactual utility vector
        # u(a, b_t) for all own actions a).
        strategies_used = {0: s1, 1: s2}
        opp_action = {0: a2, 1: a1}
        for i, agent in self.adaptive.items():
            agent.update(
                strategies_used[i] if strategies_used[i] is not None
                else agent.current_strategy(),
                [a1, a2][i],
                action_utilities_against(opp_action[i]),
            )

        row = {
            "round": self.rounds_played + 1,
            "p1_action": a1,
            "p2_action": a2,
            "p1_action_name": ACTIONS[a1],
            "p2_action_name": ACTIONS[a2],
            "p1_payoff": u1,
            "scores": list(self.scores),
        }
        for i, agent in self.adaptive.items():
            row[f"p{i + 1}_adaptive_strategy"] = [float(x) for x in agent.current_strategy()]
        self.history.append(row)
        return row

    def auto_run(self) -> list[dict]:
        """Play out all remaining rounds (only valid with no human seat)."""
        if self.has_human():
            raise ValueError("auto_run is only for matches without a human seat")
        rows = []
        while not self.finished:
            rows.append(self.play_round())
        return rows

    def summary(self) -> dict:
        freqs = []
        for i in (0, 1):
            counts = np.zeros(3)
            for row in self.history:
                counts[row[f"p{i + 1}_action"]] += 1
            total = counts.sum()
            freqs.append([float(c / total) if total else 0.0 for c in counts])
        return {
            "match_id": self.match_id,
            "rounds_played": self.rounds_played,
            "rounds_total": self.rounds_total,
            "finished": self.finished,
            "scores": list(self.scores),
            "empirical_frequencies": freqs,
            "seats": [s.kind for s in self.seats],
        }


_MATCHES: dict[str, RpsMatch] = {}
_TTL_SECONDS = 3600


def _cleanup() -> None:
    cutoff = time.time() - _TTL_SECONDS
    for mid in [m for m, match in _MATCHES.items() if match.created_at < cutoff]:
        del _MATCHES[mid]


def new_match(p1: SeatSpec, p2: SeatSpec, rounds: int, seed: int = 0) -> RpsMatch:
    _cleanup()
    if not 1 <= rounds <= MAX_ROUNDS:
        raise ValueError(f"rounds must be in [1, {MAX_ROUNDS}]")
    p1.validate()
    p2.validate()
    match = RpsMatch(match_id=uuid.uuid4().hex, seats=[p1, p2], rounds_total=rounds, seed=seed)
    _MATCHES[match.match_id] = match
    return match


def get_match(match_id: str) -> RpsMatch:
    match = _MATCHES.get(match_id)
    if match is None:
        raise KeyError("Unknown or expired match id")
    return match
