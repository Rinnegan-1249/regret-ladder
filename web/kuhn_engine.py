"""Kuhn Poker match engine for the website, on OpenSpiel game states.

Seats are either "human" or a bot id from web.bots. At most one human seat
(hot-seat human-vs-human would leak private cards through one screen).
The human only ever sees their own card and the betting history; the
opponent's card is revealed at the end of a hand only if it reaches
showdown (a fold ends the hand without reveal).
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

import numpy as np
import pyspiel

from poker_ai.evaluation.tournament import call_agent_act
from poker_ai.evaluation.stats import summarize_payoffs

from web.bots import make_kuhn_bot

MAX_HUMAN_HANDS = 200
MAX_AUTO_HANDS = 10_000
CARD_NAMES = {0: "Jack", 1: "Queen", 2: "King"}
ACTION_NAMES = {0: "pass/fold", 1: "bet/call"}


def _is_showdown(betting: str) -> bool:
    """Fold iff the last action is a pass facing a bet; otherwise showdown."""
    return not (len(betting) >= 2 and betting[-1] == "p" and betting[-2] == "b")


@dataclass
class KuhnMatch:
    match_id: str
    seats: list[str]  # "human" or bot id
    hands_total: int
    seed: int = 0
    created_at: float = field(default_factory=time.time)
    payoffs_p1: list[float] = field(default_factory=list)  # per hand, seat 0 perspective
    last_hand: dict | None = None

    def __post_init__(self):
        self.game = pyspiel.load_game("kuhn_poker")
        self.rng = np.random.default_rng(self.seed)
        self.agents = {
            i: (None if s == "human" else make_kuhn_bot(s, seed=self.seed + 100 + i))
            for i, s in enumerate(self.seats)
        }
        self.human_seat = next((i for i, s in enumerate(self.seats) if s == "human"), None)
        self.state = None
        if self.human_seat is not None:
            self._start_hand()

    @property
    def hands_played(self) -> int:
        return len(self.payoffs_p1)

    @property
    def finished(self) -> bool:
        return self.hands_played >= self.hands_total

    def _start_hand(self) -> None:
        self.state = self.game.new_initial_state()
        self._advance()

    def _advance(self) -> None:
        """Apply chance and bot actions until human's turn or terminal."""
        while not self.state.is_terminal():
            if self.state.is_chance_node():
                outcomes = self.state.chance_outcomes()
                actions = [a for a, _ in outcomes]
                probs = np.asarray([p for _, p in outcomes], dtype=np.float64)
                probs = probs / probs.sum()
                self.state.apply_action(int(self.rng.choice(actions, p=probs)))
                continue
            player = self.state.current_player()
            if player == self.human_seat:
                return
            action = call_agent_act(self.agents[player], self.state, self.rng)
            self.state.apply_action(int(action))
        self._finish_hand()

    def _finish_hand(self) -> None:
        returns = self.state.returns()
        history = self.state.history()  # [p0 card, p1 card, betting...]
        betting = "".join("pb"[a] for a in history[2:])
        showdown = _is_showdown(betting)
        self.last_hand = {
            "hand": self.hands_played + 1,
            "betting": betting,
            "payoffs": [float(returns[0]), float(returns[1])],
            "showdown": showdown,
            "cards": (
                {"p1": CARD_NAMES[history[0]], "p2": CARD_NAMES[history[1]]}
                if showdown or self.human_seat is None
                else {f"p{self.human_seat + 1}": CARD_NAMES[history[self.human_seat]]}
            ),
        }
        self.payoffs_p1.append(float(returns[0]))
        if not self.finished and self.human_seat is not None:
            self._start_hand()

    def view(self) -> dict:
        """Human-visible state: own card + betting history only."""
        out = {
            "match_id": self.match_id,
            "hands_played": self.hands_played,
            "hands_total": self.hands_total,
            "finished": self.finished,
            "totals": [sum(self.payoffs_p1), -sum(self.payoffs_p1)],
            "seats": list(self.seats),
            "last_hand": self.last_hand,
        }
        if self.human_seat is not None and not self.finished and not self.state.is_terminal():
            info = self.state.information_state_string(self.human_seat)
            out["to_act"] = self.state.current_player() == self.human_seat
            out["your_seat"] = self.human_seat + 1
            out["your_card"] = CARD_NAMES[int(info[0])]
            out["betting"] = info[1:]
            out["legal_actions"] = [
                {"action": a, "label": ACTION_NAMES[a]} for a in self.state.legal_actions()
            ]
        return out

    def act(self, action: int) -> dict:
        if self.human_seat is None:
            raise ValueError("No human seat in this match")
        if self.finished:
            raise ValueError("Match already finished")
        if self.state.current_player() != self.human_seat:
            raise ValueError("Not the human's turn")
        if action not in self.state.legal_actions():
            raise ValueError(f"Illegal action {action}; legal: {self.state.legal_actions()}")
        self.state.apply_action(int(action))
        self._advance()
        return self.view()

    def auto_run(self) -> dict:
        """Simulate all hands bot-vs-bot and return aggregate stats."""
        if self.human_seat is not None:
            raise ValueError("auto_run is only for bot-vs-bot matches")
        from poker_ai.evaluation.tournament import play_one_hand

        agents = [self.agents[0], self.agents[1]]
        while not self.finished:
            returns = play_one_hand(self.game, agents, self.rng)
            self.payoffs_p1.append(float(returns[0]))
        stats = summarize_payoffs(np.asarray(self.payoffs_p1))
        return {
            "match_id": self.match_id,
            "hands": self.hands_played,
            "p1_mean_payoff": stats.mean,
            "ci_low": stats.ci_low,
            "ci_high": stats.ci_high,
            "p1_win_rate": stats.win_rate,
            "totals": [sum(self.payoffs_p1), -sum(self.payoffs_p1)],
            "seats": list(self.seats),
        }


_MATCHES: dict[str, KuhnMatch] = {}
_TTL_SECONDS = 3600


def _cleanup() -> None:
    cutoff = time.time() - _TTL_SECONDS
    for mid in [m for m, match in _MATCHES.items() if match.created_at < cutoff]:
        del _MATCHES[mid]


def new_match(p1: str, p2: str, hands: int, seed: int = 0) -> KuhnMatch:
    _cleanup()
    seats = [p1, p2]
    n_humans = seats.count("human")
    if n_humans > 1:
        raise ValueError("At most one human seat (private cards would leak)")
    cap = MAX_HUMAN_HANDS if n_humans else MAX_AUTO_HANDS
    if not 1 <= hands <= cap:
        raise ValueError(f"hands must be in [1, {cap}] for this seat combination")
    match = KuhnMatch(match_id=uuid.uuid4().hex, seats=seats, hands_total=hands, seed=seed)
    _MATCHES[match.match_id] = match
    return match


def get_match(match_id: str) -> KuhnMatch:
    match = _MATCHES.get(match_id)
    if match is None:
        raise KeyError("Unknown or expired match id")
    return match
