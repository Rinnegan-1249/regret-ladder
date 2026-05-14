"""Observer script for one OpenSpiel poker hand.

This script is intentionally verbose. It prints the OpenSpiel game/state functions
used by the Week 1 tournament code, so you can explain to a professor what is
happening inside one hand between two baseline bots.

Example:
    python scripts/observe_openspiel_game.py --game kuhn_poker --agent-a random --agent-b always_call --seed 0

Output:
    results/logs/observe_kuhn_poker_random_vs_always_call_seed0.txt
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pyspiel

from poker_ai.agents.always_call import AlwaysCallAgent
from poker_ai.agents.always_fold import AlwaysFoldAgent
from poker_ai.agents.ev_heuristic import EVHeuristicAgent
from poker_ai.agents.random_agent import RandomAgent
from poker_ai.agents.rule_based import RuleBasedAgent


AGENT_FACTORIES = {
    "random": lambda seed: RandomAgent(seed=seed),
    "always_call": lambda seed: AlwaysCallAgent(),
    "always_fold": lambda seed: AlwaysFoldAgent(),
    "rule_based": lambda seed: RuleBasedAgent(),
    "ev_heuristic": lambda seed: EVHeuristicAgent(seed=seed),
}


def safe_call(label: str, fn, default: str = "<not available>") -> str:
    """Call an OpenSpiel method safely and stringify the result for logging."""
    try:
        value = fn()
        return f"{label}: {value}"
    except Exception as exc:  # pragma: no cover - this is an observer/debug script
        return f"{label}: {default} ({type(exc).__name__}: {exc})"


def action_to_string(game: Any, state: Any, player: int, action: int) -> str:
    """Best-effort conversion of an OpenSpiel action id to a readable string."""
    attempts = [
        lambda: state.action_to_string(player, action),
        lambda: game.action_to_string(player, action),
        lambda: state.action_to_string(action),
    ]
    for attempt in attempts:
        try:
            return str(attempt())
        except Exception:
            pass
    return str(action)


def legal_actions_with_names(game: Any, state: Any, player: int) -> list[str]:
    """Return legal action ids with readable names when OpenSpiel exposes them."""
    actions = state.legal_actions()
    return [f"{a} ({action_to_string(game, state, player, int(a))})" for a in actions]


def log_game_header(lines: list[str], game: Any, game_name: str) -> None:
    """Log game-level information. These functions come from OpenSpiel."""
    lines.append("=" * 88)
    lines.append("OPEN-SPIEL GAME-LEVEL FUNCTIONS")
    lines.append("=" * 88)
    lines.append(f"pyspiel.load_game({game_name!r}) -> OpenSpiel Game object")
    lines.append(safe_call("game.get_type()", lambda: game.get_type()))
    lines.append(safe_call("game.num_players()", lambda: game.num_players()))
    lines.append(safe_call("game.num_distinct_actions()", lambda: game.num_distinct_actions()))
    lines.append(safe_call("game.max_game_length()", lambda: game.max_game_length()))
    lines.append(safe_call("game.min_utility()", lambda: game.min_utility()))
    lines.append(safe_call("game.max_utility()", lambda: game.max_utility()))
    lines.append(safe_call("game.utility_sum()", lambda: game.utility_sum()))
    lines.append("")
    lines.append("Interpretation:")
    lines.append("- OpenSpiel gives the rules of the game: players, actions, chance events, and payoffs.")
    lines.append("- Our code does not manually implement Kuhn Poker rules; it asks OpenSpiel for them.")
    lines.append("")


def log_state_snapshot(lines: list[str], game: Any, state: Any, label: str) -> None:
    """Log the current state using OpenSpiel state-level methods."""
    lines.append("-" * 88)
    lines.append(label)
    lines.append("-" * 88)
    lines.append(safe_call("str(state)", lambda: str(state)))
    lines.append(safe_call("state.history()", lambda: state.history()))
    lines.append(safe_call("state.is_terminal()", lambda: state.is_terminal()))
    lines.append(safe_call("state.is_chance_node()", lambda: state.is_chance_node()))
    lines.append(safe_call("state.current_player()", lambda: state.current_player()))

    if not state.is_terminal() and not state.is_chance_node():
        player = state.current_player()
        lines.append(safe_call(f"state.legal_actions(player={player})", lambda: state.legal_actions()))
        lines.append(f"legal action names: {legal_actions_with_names(game, state, player)}")
        lines.append(
            safe_call(
                f"state.information_state_string(player={player})",
                lambda: state.information_state_string(player),
            )
        )
        lines.append(
            safe_call(
                f"state.observation_string(player={player})",
                lambda: state.observation_string(player),
            )
        )
    elif state.is_chance_node():
        outcomes = state.chance_outcomes()
        pretty = []
        for action, prob in outcomes:
            pretty.append(f"{action} ({action_to_string(game, state, pyspiel.PlayerId.CHANCE, int(action))}) with p={prob}")
        lines.append(f"state.chance_outcomes(): {pretty}")
    else:
        lines.append(safe_call("state.returns()", lambda: state.returns()))
    lines.append("")


def observe_one_hand(
    game_name: str,
    agent_a_name: str,
    agent_b_name: str,
    seed: int,
    output_path: Path,
) -> None:
    if agent_a_name not in AGENT_FACTORIES:
        raise ValueError(f"Unknown --agent-a {agent_a_name!r}. Choices: {sorted(AGENT_FACTORIES)}")
    if agent_b_name not in AGENT_FACTORIES:
        raise ValueError(f"Unknown --agent-b {agent_b_name!r}. Choices: {sorted(AGENT_FACTORIES)}")

    rng = np.random.default_rng(seed)
    game = pyspiel.load_game(game_name)
    agents = [AGENT_FACTORIES[agent_a_name](seed + 101), AGENT_FACTORIES[agent_b_name](seed + 202)]
    state = game.new_initial_state()

    lines: list[str] = []
    lines.append("Observer transcript for one OpenSpiel poker hand")
    lines.append(f"Game: {game_name}")
    lines.append(f"Player 0 bot: {agent_a_name}")
    lines.append(f"Player 1 bot: {agent_b_name}")
    lines.append(f"Seed: {seed}")
    lines.append("")

    log_game_header(lines, game, game_name)
    lines.append("=" * 88)
    lines.append("ONE-HAND TRANSCRIPT: OBSERVER VIEW")
    lines.append("=" * 88)
    lines.append("At each step, the observer asks OpenSpiel what kind of state we are in.")
    lines.append("If it is a chance node, OpenSpiel gives card-deal outcomes and probabilities.")
    lines.append("If it is a player node, OpenSpiel gives legal actions; our bot chooses one.")
    lines.append("")

    step = 0
    log_state_snapshot(lines, game, state, f"Initial state before step {step}")

    while not state.is_terminal():
        lines.append("#" * 88)
        lines.append(f"STEP {step}")
        lines.append("#" * 88)

        if state.is_chance_node():
            outcomes = state.chance_outcomes()
            actions, probs = zip(*outcomes)
            probs_array = np.array(probs, dtype=float)
            action = int(rng.choice(actions, p=probs_array))
            lines.append("Node type: CHANCE / card-dealing node")
            lines.append("OpenSpiel function used: state.chance_outcomes()")
            lines.append(f"Possible chance outcomes: {list(outcomes)}")
            lines.append(f"Our NumPy RNG seed stream samples action: {action}")
            lines.append(f"Readable action: {action_to_string(game, state, pyspiel.PlayerId.CHANCE, action)}")
            lines.append("OpenSpiel function used next: state.apply_action(sampled_chance_action)")
            state.apply_action(action)
        else:
            player = state.current_player()
            legal = state.legal_actions()
            info_state = state.information_state_string(player)
            action = int(agents[player].act(state))
            lines.append(f"Node type: PLAYER DECISION node")
            lines.append(f"OpenSpiel says current player is: {player}")
            lines.append(f"Bot controlling this player: {agent_a_name if player == 0 else agent_b_name}")
            lines.append(f"OpenSpiel legal actions: {legal}")
            lines.append(f"Readable legal actions: {legal_actions_with_names(game, state, player)}")
            lines.append(f"OpenSpiel information state for player {player}: {info_state}")
            lines.append(f"Bot-selected action id: {action}")
            lines.append(f"Bot-selected action name: {action_to_string(game, state, player, action)}")

            if action not in legal:
                raise ValueError(f"Bot chose illegal action {action}; legal actions were {legal}")

            lines.append("OpenSpiel function used next: state.apply_action(bot_selected_action)")
            state.apply_action(action)

        step += 1
        log_state_snapshot(lines, game, state, f"State after step {step}")

    lines.append("=" * 88)
    lines.append("TERMINAL RESULT")
    lines.append("=" * 88)
    returns = state.returns()
    lines.append(f"OpenSpiel final returns: state.returns() -> {returns}")
    lines.append(f"Payoff to Player 0 / {agent_a_name}: {returns[0]}")
    lines.append(f"Payoff to Player 1 / {agent_b_name}: {returns[1]}")
    lines.append("")
    lines.append("What this shows:")
    lines.append("1. OpenSpiel runs the game rules and validates legal transitions.")
    lines.append("2. Our agents only choose among OpenSpiel's legal actions.")
    lines.append("3. The seed controls our NumPy sampling of chance outcomes / stochastic bots.")
    lines.append("4. state.apply_action(...) is what actually moves the hand forward.")
    lines.append("5. state.returns() gives the final payoff vector used by tournament.py.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote observer transcript to: {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print an observer transcript for one OpenSpiel poker hand.")
    parser.add_argument("--game", default="kuhn_poker", help="OpenSpiel game name, e.g. kuhn_poker or leduc_poker")
    parser.add_argument("--agent-a", default="random", choices=sorted(AGENT_FACTORIES))
    parser.add_argument("--agent-b", default="always_call", choices=sorted(AGENT_FACTORIES))
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", default=None, help="Optional output text path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.output is None:
        output = Path(
            f"results/logs/observe_{args.game}_{args.agent_a}_vs_{args.agent_b}_seed{args.seed}.txt"
        )
    else:
        output = Path(args.output)
    observe_one_hand(args.game, args.agent_a, args.agent_b, args.seed, output)


if __name__ == "__main__":
    main()
