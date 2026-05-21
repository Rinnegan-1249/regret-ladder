from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable

import numpy as np
import pyspiel

from poker_ai.agents.always_call import AlwaysCallAgent
from poker_ai.agents.always_fold import AlwaysFoldAgent
from poker_ai.agents.ev_heuristic import EVHeuristicAgent
from poker_ai.agents.random_agent import RandomAgent
from poker_ai.agents.rule_based import RuleBasedAgent


def build_bot(name: str, seed: int):
    factories: dict[str, Callable[[], object]] = {
        "random": lambda: RandomAgent(seed=10_000 + seed),
        "always_call": AlwaysCallAgent,
        "always_fold": AlwaysFoldAgent,
        "rule_based": RuleBasedAgent,
        "ev_heuristic": lambda: EVHeuristicAgent(seed=20_000 + seed),
    }
    if name not in factories:
        raise ValueError(f"Unknown bot {name}. Choose from: {sorted(factories)}")
    return factories[name]()


def action_name(state, action: int) -> str:
    history = str(state).split()
    public = "" if len(history) <= 2 else history[-1]
    facing_bet = public.endswith("b")
    if action == 0:
        return "Pass/check" if not facing_bet else "Pass/fold"
    if action == 1:
        return "Bet" if not facing_bet else "Call"
    return f"Action {action}"


def play_one_hand(game, agents, deal_seed: int, out_lines: list[str], title: str):
    rng = np.random.default_rng(deal_seed)
    state = game.new_initial_state()

    def log(line: str = ""):
        print(line)
        out_lines.append(line)

    log("=" * 90)
    log(title)
    log("=" * 90)

    step = 0
    while not state.is_terminal():
        log(f"\nSTEP {step}")
        log(f"str(state): {str(state)}")
        log(f"state.history(): {state.history()}")
        log(f"state.current_player(): {state.current_player()}")

        if state.is_chance_node():
            outcomes = state.chance_outcomes()
            actions, probs = zip(*outcomes)
            action = int(rng.choice(actions, p=np.array(probs, dtype=float)))
            log(f"CHANCE state.chance_outcomes(): {outcomes}")
            log(f"Sampled chance action from deal_seed={deal_seed}: {action}")
            state.apply_action(action)
        else:
            player = state.current_player()
            agent = agents[player]
            legal = state.legal_actions()
            log(f"PLAYER {player}: {agent.name}")
            log(f"state.information_state_string(player={player}): {state.information_state_string(player)}")
            log(f"state.observation_string(player={player}): {state.observation_string(player)}")
            log(f"state.legal_actions(): {legal}")
            log(f"Readable legal actions: {[f'{a} ({action_name(state, a)})' for a in legal]}")
            action = int(agent.act(state))
            if action not in legal:
                raise ValueError(f"{agent.name} chose illegal action {action}; legal={legal}")
            log(f"Chosen action: {action} ({action_name(state, action)})")
            state.apply_action(action)

        step += 1

    returns = np.array(state.returns(), dtype=float)
    log("\nTERMINAL")
    log(f"str(state): {str(state)}")
    log(f"state.history(): {state.history()}")
    log(f"state.returns(): {returns.tolist()}")
    return returns


def parse_matchup(text: str) -> tuple[str, str]:
    if ":" not in text:
        raise ValueError("Matchups must look like ev_heuristic:rule_based")
    a, b = text.split(":", 1)
    return a.strip(), b.strip()


def main():
    parser = argparse.ArgumentParser(description="Bot-vs-bot duplicate-pair demo.")
    parser.add_argument("--game", default="kuhn_poker", choices=["kuhn_poker", "leduc_poker"])
    parser.add_argument("--matchups", nargs="+", default=["ev_heuristic:rule_based", "ev_heuristic:always_call"])
    parser.add_argument("--pairs-per-matchup", type=int, default=1)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", default="results/logs/bot_demo.txt")
    args = parser.parse_args()

    game = pyspiel.load_game(args.game)
    out_lines: list[str] = []
    summary_rows = []

    for m_idx, matchup in enumerate(args.matchups):
        agent_a_name, agent_b_name = parse_matchup(matchup)

        for pair in range(args.pairs_per_matchup):
            deal_seed = args.seed * 1_000_000 + m_idx * 10_000 + pair

            agent_a = build_bot(agent_a_name, seed=args.seed + m_idx)
            agent_b = build_bot(agent_b_name, seed=args.seed + m_idx)
            u_ab = play_one_hand(
                game,
                [agent_a, agent_b],
                deal_seed,
                out_lines,
                title=f"{agent_a_name} vs {agent_b_name}, pair={pair}, hand A: A=P0, B=P1",
            )

            agent_a = build_bot(agent_a_name, seed=args.seed + m_idx)
            agent_b = build_bot(agent_b_name, seed=args.seed + m_idx)
            u_ba = play_one_hand(
                game,
                [agent_b, agent_a],
                deal_seed,
                out_lines,
                title=f"{agent_a_name} vs {agent_b_name}, pair={pair}, hand B: B=P0, A=P1, same deal_seed",
            )

            payoff_to_a = 0.5 * (float(u_ab[0]) + float(u_ba[1]))
            summary_rows.append((agent_a_name, agent_b_name, pair, deal_seed, payoff_to_a))

    out_lines.append("")
    out_lines.append("=" * 90)
    out_lines.append("BOT DEMO SUMMARY")
    out_lines.append("=" * 90)
    for a, b, pair, deal_seed, payoff in summary_rows:
        line = f"{a} vs {b}, duplicate_pair={pair}, deal_seed={deal_seed}, paired payoff to {a}: {payoff:.4f}"
        print(line)
        out_lines.append(line)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"\nSaved transcript to: {out}")


if __name__ == "__main__":
    main()
