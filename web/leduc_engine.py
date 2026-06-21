"""Leduc Poker match engine for the website - LIVE FastAPI mode only.

Not used by the static GitHub Pages export (which uses precomputed
walkthroughs instead, see web/templates/leduc.html's static_mode branch) -
this engine only runs against the live Render/uvicorn deployment.

Mirrors web/kuhn_engine.py's design: seats are either "human" or a bot id
from web.bots. At most one human seat. The human sees their own card, the
public card once it's dealt, and the betting log for both rounds; the
opponent's card is revealed only at showdown (a fold ends the hand without
a reveal).
"""
from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field

import numpy as np
import pyspiel

from poker_ai.evaluation.tournament import call_agent_act, play_one_hand
from poker_ai.evaluation.stats import summarize_payoffs

from web.bots import make_leduc_bot

MAX_HUMAN_HANDS = 200
MAX_AUTO_HANDS = 10_000
CARD_NAMES = {0: "Jack", 1: "Jack", 2: "Queen", 3: "Queen", 4: "King", 5: "King"}
_POT_RE = re.compile(r"\[Pot: (\d+)\]")


def _action_label(action: int, bet_pending: bool) -> str:
    if action == 0:
        return "Fold"
    if action == 1:
        return "Call" if bet_pending else "Check"
    return "Raise" if bet_pending else "Bet"


@dataclass
class LeducMatch:
    match_id: str
    seats: list[str]  # "human" or bot id
    hands_total: int
    seed: int = 0
    created_at: float = field(default_factory=time.time)
    payoffs_p1: list[float] = field(default_factory=list)  # per hand, seat 0 perspective
    last_hand: dict | None = None

    def __post_init__(self):
        self.game = pyspiel.load_game("leduc_poker")
        self.rng = np.random.default_rng(self.seed)
        self.agents = {
            i: (None if s == "human" else make_leduc_bot(s, seed=self.seed + 100 + i))
            for i, s in enumerate(self.seats)
        }
        self.human_seat = next((i for i, s in enumerate(self.seats) if s == "human"), None)
        self.state = None
        self._reset_hand_state()
        if self.human_seat is not None:
            self._start_hand()

    @property
    def hands_played(self) -> int:
        return len(self.payoffs_p1)

    @property
    def finished(self) -> bool:
        return self.hands_played >= self.hands_total

    def _reset_hand_state(self) -> None:
        self.private = [None, None]
        self.public_card = None
        self.round1_log: list[dict] = []
        self.round2_log: list[dict] = []
        self.bet_pending = False
        self.n_chance_seen = 0

    def _start_hand(self) -> None:
        self.state = self.game.new_initial_state()
        self._reset_hand_state()
        self._advance()

    def _current_pot(self) -> int:
        info = self.state.information_state_string(self.state.current_player())
        m = _POT_RE.search(info)
        return int(m.group(1)) if m else 2

    def _apply_logged_action(self, player: int, action: int) -> None:
        label = _action_label(action, self.bet_pending)
        (self.round2_log if self.public_card else self.round1_log).append(
            {"player": player, "label": label}
        )
        self.bet_pending = action == 2
        self.state.apply_action(action)

    def _advance(self) -> None:
        """Apply chance and bot actions until human's turn or terminal."""
        while not self.state.is_terminal():
            if self.state.is_chance_node():
                outcomes = self.state.chance_outcomes()
                actions = [a for a, _ in outcomes]
                probs = np.asarray([p for _, p in outcomes], dtype=np.float64)
                probs = probs / probs.sum()
                action = int(self.rng.choice(actions, p=probs))
                self.state.apply_action(action)
                if self.n_chance_seen < 2:
                    self.private[self.n_chance_seen] = CARD_NAMES[action]
                else:
                    self.public_card = CARD_NAMES[action]
                    self.bet_pending = False
                self.n_chance_seen += 1
                continue
            player = self.state.current_player()
            if player == self.human_seat:
                return
            action = call_agent_act(self.agents[player], self.state, self.rng)
            self._apply_logged_action(player, int(action))
        self._finish_hand()

    def _finish_hand(self) -> None:
        returns = self.state.returns()
        last_log = self.round2_log or self.round1_log or [{}]
        folded = last_log[-1].get("label") == "Fold"
        self.last_hand = {
            "hand": self.hands_played + 1,
            "public_card": self.public_card,
            "round1_log": list(self.round1_log),
            "round2_log": list(self.round2_log),
            "payoffs": [float(returns[0]), float(returns[1])],
            "showdown": not folded,
            "cards": (
                {"p1": self.private[0], "p2": self.private[1]}
                if (not folded) or self.human_seat is None
                else {f"p{self.human_seat + 1}": self.private[self.human_seat]}
            ),
        }
        self.payoffs_p1.append(float(returns[0]))
        if not self.finished and self.human_seat is not None:
            self._start_hand()

    def view(self) -> dict:
        """Human-visible state: own card, public card, betting logs only."""
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
            out["your_seat"] = self.human_seat + 1
            out["your_card"] = self.private[self.human_seat]
            out["public_card"] = self.public_card
            out["pot"] = self._current_pot()
            out["round1_log"] = list(self.round1_log)
            out["round2_log"] = list(self.round2_log)
            out["to_act"] = self.state.current_player() == self.human_seat
            if out["to_act"]:
                out["legal_actions"] = [
                    {"action": a, "label": _action_label(a, self.bet_pending)}
                    for a in self.state.legal_actions()
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
        self._apply_logged_action(self.human_seat, int(action))
        self._advance()
        return self.view()

    def auto_run(self) -> dict:
        """Simulate all hands bot-vs-bot and return aggregate stats."""
        if self.human_seat is not None:
            raise ValueError("auto_run is only for bot-vs-bot matches")
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


_MATCHES: dict[str, LeducMatch] = {}
_TTL_SECONDS = 3600


def _cleanup() -> None:
    cutoff = time.time() - _TTL_SECONDS
    for mid in [m for m, match in _MATCHES.items() if match.created_at < cutoff]:
        del _MATCHES[mid]


def new_match(p1: str, p2: str, hands: int, seed: int = 0) -> LeducMatch:
    _cleanup()
    seats = [p1, p2]
    n_humans = seats.count("human")
    if n_humans > 1:
        raise ValueError("At most one human seat (private cards would leak)")
    cap = MAX_HUMAN_HANDS if n_humans else MAX_AUTO_HANDS
    if not 1 <= hands <= cap:
        raise ValueError(f"hands must be in [1, {cap}] for this seat combination")
    match = LeducMatch(match_id=uuid.uuid4().hex, seats=seats, hands_total=hands, seed=seed)
    _MATCHES[match.match_id] = match
    return match


def get_match(match_id: str) -> LeducMatch:
    match = _MATCHES.get(match_id)
    if match is None:
        raise KeyError("Unknown or expired match id")
    return match
