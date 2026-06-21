"""Offline precompute for the static (GitHub Pages) web export.

Bakes everything the static site needs into web/static/data/ so the browser
never has to run a solver or hit a server:
  (a) frozen bot policy tables (web/static/data/policies/) - reuses the
      same cached training the FastAPI app already does (web/bots.py).
  (b) training-replay checkpoint arrays (web/static/data/training/) for the
      "live" training charts - RPS/Kuhn reuse web/training_stream.py's exact
      checkpoint logic; Leduc reuses the already-validated, already-committed
      results/tables/week05_leduc_cfr_variants.csv (no retraining).
  (c) fixed example-hand walkthroughs (web/static/data/walkthroughs/) for the
      Kuhn and Leduc "play" tabs - a few deterministic seeded hands against
      the trained CFR+ bot.

Safe to rerun any time content changes; everything here is deterministic
given a fixed seed. Run from the repo root:
    .venv/Scripts/python.exe scripts/build_web_static_data.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # make poker_ai *and* web importable as packages

import numpy as np
import pyspiel

from poker_ai.agents.regret_matching import RegretMatchingAgent
from poker_ai.env.rps import PAYOFF_MATRIX
from poker_ai.evaluation.exploitability import compute_exploitability
from poker_ai.evaluation.tournament import call_agent_act

from web import bots
from web import training_stream
from web.kuhn_engine import KuhnMatch

DATA = ROOT / "web" / "static" / "data"
POLICIES_DIR = DATA / "policies"
TRAINING_DIR = DATA / "training"
WALKTHROUGHS_DIR = DATA / "walkthroughs"

LEDUC_CARD_NAMES = {0: "Jack", 1: "Jack", 2: "Queen", 3: "Queen", 4: "King", 5: "King"}
_POT_RE = re.compile(r"\[Pot: (\d+)\]")


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    print(f"  wrote {path.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# (a) Policy tables
# ---------------------------------------------------------------------------

def build_policies() -> None:
    print("Policies:")
    _write_json(POLICIES_DIR / "rps_frozen.json", bots.get_rps_frozen_strategy())
    for bot_id in bots.KUHN_CFR_BOTS:
        _write_json(POLICIES_DIR / f"kuhn_{bot_id}.json", bots.get_kuhn_policy_table(bot_id))
    for bot_id in bots.LEDUC_CFR_BOTS:
        _write_json(POLICIES_DIR / f"leduc_{bot_id}.json", bots.get_leduc_policy_table(bot_id))


# ---------------------------------------------------------------------------
# (b) Training replay checkpoints
# ---------------------------------------------------------------------------

def build_rps_training_replay() -> None:
    iterations, seed = 20_000, 0
    pts = sorted(training_stream._checkpoints(iterations))
    p1 = RegretMatchingAgent(num_actions=3, seed=seed)
    p2 = RegretMatchingAgent(num_actions=3, seed=seed + 10_000)
    p1.regret_sum[:] = p1.rng.uniform(0.0, 1.0, size=3)
    p2.regret_sum[:] = p2.rng.uniform(0.0, 1.0, size=3)
    events = [{"type": "start", "iterations": iterations, "seed": seed}]
    t = 0
    for checkpoint in pts:
        for _ in range(t + 1, checkpoint + 1):
            s1, s2 = p1.current_strategy(), p2.current_strategy()
            p1.update_expected(s1, PAYOFF_MATRIX @ s2)
            p2.update_expected(s2, PAYOFF_MATRIX @ s1)
        t = checkpoint
        events.append({
            "type": "checkpoint", "t": t,
            "p1_avg": [float(x) for x in p1.average_strategy()],
            "p2_avg": [float(x) for x in p2.average_strategy()],
            "p1_avg_regret": p1.average_regret(),
            "p2_avg_regret": p2.average_regret(),
        })
    events.append({"type": "done"})
    _write_json(TRAINING_DIR / "rps.json", {"events": events})


def build_kuhn_training_replay() -> None:
    game = pyspiel.load_game("kuhn_poker")
    for algo, (label, cap, _takes_seed) in training_stream.KUHN_ALGOS.items():
        seed = 0
        solver = training_stream._make_kuhn_solver(algo, game, seed)
        pts = sorted(training_stream._checkpoints(cap))
        events = [{"type": "start", "algo": algo, "label": label, "iterations": cap, "seed": seed}]
        t = 0
        for checkpoint in pts:
            for _ in range(checkpoint - t):
                solver.step()
            t = checkpoint
            events.append({
                "type": "checkpoint", "t": t,
                "exploitability": compute_exploitability(game, solver.average_policy()),
                "bet_probs": training_stream._avg_bet_probs(solver),
            })
        events.append({"type": "done"})
        _write_json(TRAINING_DIR / f"kuhn_{algo}.json", {"events": events})


def build_leduc_training_replay() -> None:
    """No retraining - reuse the already-validated, already-committed Week 5/6
    CSVs directly. CFR/CFR+ come from week05 (10k-iteration run, has the
    zero-regret-fraction column); OS-MCCFR/ES-MCCFR come from week06's seed-0
    series (500k/100k-iteration runs) - the two CSVs use unrelated iteration
    scales, so the four series are replayed positionally (one point per
    series per animation step), not on a shared iteration axis."""
    week05 = ROOT / "results" / "tables" / "week05_leduc_cfr_variants.csv"
    week06 = ROOT / "results" / "tables" / "week06_leduc_mccfr.csv"

    cfr_pts, cfrplus_pts = [], []
    with week05.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cfr_pts.append({
                "t": int(row["iteration"]), "expl": float(row["cfr_avg_expl"]),
                "zero_regret_frac": float(row["cfr_zero_regret_frac"]),
            })
            cfrplus_pts.append({
                "t": int(row["iteration"]), "expl": float(row["cfrplus_avg_expl"]),
                "zero_regret_frac": float(row["cfrplus_zero_regret_frac"]),
            })

    os_pts, es_pts = [], []
    with week06.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["seed"] != "0":
                continue
            pt = {"t": int(row["iteration"]), "expl": float(row["exploitability"])}
            if row["algorithm"] == "OS-MCCFR":
                os_pts.append(pt)
            elif row["algorithm"] == "ES-MCCFR":
                es_pts.append(pt)

    n_steps = max(len(cfr_pts), len(cfrplus_pts), len(os_pts), len(es_pts))

    def at(series, i):
        return series[min(i, len(series) - 1)]

    events = [{"type": "start"}]
    for i in range(n_steps):
        events.append({
            "type": "checkpoint",
            "cfr": at(cfr_pts, i),
            "cfrplus": at(cfrplus_pts, i),
            "os_mccfr": at(os_pts, i),
            "es_mccfr": at(es_pts, i),
        })
    events.append({"type": "done"})
    _write_json(TRAINING_DIR / "leduc.json", {"events": events})


# ---------------------------------------------------------------------------
# (c) Fixed example-hand walkthroughs
# ---------------------------------------------------------------------------

def build_kuhn_walkthroughs() -> list[dict]:
    """Reuses kuhn_engine.KuhnMatch exactly as the live API does: seat 0 is
    "human" so the engine pauses at its turn, but instead of real input we
    drive it with the CFR+ bot's own policy (acting as a narrator), recording
    the view() returned after every action - byte-identical to what a real
    human click would have received."""
    manifest = []
    opponent_id = "always_call"
    for n, seed in enumerate([0, 1, 2], start=1):
        match = KuhnMatch(match_id=f"walk-{n}", seats=["human", opponent_id], hands_total=4, seed=seed)
        narrator = bots.make_kuhn_bot("cfr_plus", seed=seed + 999)
        views = [match.view()]
        while not match.finished:
            view = views[-1]
            if not view.get("to_act"):
                break  # shouldn't happen: human_seat=0 always has to_act when not finished
            action = int(call_agent_act(narrator, match.state, match.rng))
            facing_bet = (view.get("betting") or "").endswith("b")
            if action == 1:
                view["_next_action_label"] = "CALL" if facing_bet else "BET"
            else:
                view["_next_action_label"] = "FOLD" if facing_bet else "CHECK"
            views.append(match.act(action))
        seat_labels = ["CFR+ (narrated)", bots.KUHN_BASELINE_BOTS[opponent_id][0]]
        _write_json(WALKTHROUGHS_DIR / f"kuhn_{n}.json", {
            "human_seat": 0, "seat_labels": seat_labels, "views": views,
        })
        manifest.append({"id": str(n), "label": f"CFR+ vs {seat_labels[1]} ({match.hands_total} hands, seed {seed})"})
    return manifest


def _leduc_action_label(action: int, bet_pending: bool) -> str:
    if action == 0:
        return "Fold"
    if action == 1:
        return "Call" if bet_pending else "Check"
    return "Raise" if bet_pending else "Bet"


def _play_leduc_hand(game, agents, rng) -> dict:
    state = game.new_initial_state()
    private = [None, None]
    public_card = None
    round1_actions: list[dict] = []
    round2_actions: list[dict] = []
    n_chance_seen = 0
    bet_pending = False
    last_pot = 2  # antes

    while not state.is_terminal():
        if state.is_chance_node():
            outcomes = state.chance_outcomes()
            actions = [a for a, _ in outcomes]
            probs = np.asarray([p for _, p in outcomes], dtype=np.float64)
            action = int(rng.choice(actions, p=probs / probs.sum()))
            state.apply_action(action)
            if n_chance_seen < 2:
                private[n_chance_seen] = LEDUC_CARD_NAMES[action]
            else:
                public_card = LEDUC_CARD_NAMES[action]
                bet_pending = False
            n_chance_seen += 1
            continue
        player = state.current_player()
        m = _POT_RE.search(state.information_state_string(player))
        if m:
            last_pot = int(m.group(1))
        action = int(call_agent_act(agents[player], state, rng))
        label = _leduc_action_label(action, bet_pending)
        (round2_actions if public_card else round1_actions).append({"player": player, "label": label})
        if action == 2:
            bet_pending = True
        elif action == 1:
            bet_pending = False
        state.apply_action(action)

    returns = state.returns()
    last_action = (round2_actions or round1_actions)[-1]
    folded = last_action["label"] == "Fold"
    return {
        "cards": {"p1": private[0], "p2": private[1]},
        "public_card": public_card,
        "round1_actions": round1_actions,
        "round2_actions": round2_actions,
        "pot": last_pot,
        "showdown": not folded,
        "payoffs": [float(returns[0]), float(returns[1])],
    }


def build_leduc_walkthroughs() -> list[dict]:
    game = pyspiel.load_game("leduc_poker")
    manifest = []
    opponent_id = "always_call"
    for n, seed in enumerate([0, 1, 2], start=1):
        rng = np.random.default_rng(seed)
        narrator = bots.make_leduc_bot("cfr_plus", seed=seed + 999)
        opponent = bots.make_leduc_bot(opponent_id, seed=seed + 500)
        hands = [_play_leduc_hand(game, [narrator, opponent], rng) for _ in range(4)]
        for h, hand in enumerate(hands, start=1):
            hand["hand"] = h
        seat_labels = [bots.LEDUC_CFR_BOTS["cfr_plus"][0], bots.LEDUC_BASELINE_BOTS[opponent_id][0]]
        _write_json(WALKTHROUGHS_DIR / f"leduc_{n}.json", {"seat_labels": seat_labels, "hands": hands})
        manifest.append({"id": str(n), "label": f"CFR+ vs {seat_labels[1]} (4 hands, seed {seed})"})
    return manifest


def main() -> None:
    build_policies()
    print("Training replays:")
    build_rps_training_replay()
    build_kuhn_training_replay()
    build_leduc_training_replay()
    print("Walkthroughs:")
    kuhn_manifest = build_kuhn_walkthroughs()
    leduc_manifest = build_leduc_walkthroughs()
    _write_json(WALKTHROUGHS_DIR / "manifest.json", {"kuhn": kuhn_manifest, "leduc": leduc_manifest})
    print("Done.")


if __name__ == "__main__":
    main()
