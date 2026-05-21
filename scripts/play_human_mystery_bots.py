from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pyspiel

from poker_ai.agents.always_call import AlwaysCallAgent
from poker_ai.agents.always_fold import AlwaysFoldAgent
from poker_ai.agents.ev_heuristic import EVHeuristicAgent
from poker_ai.agents.random_agent import RandomAgent
from poker_ai.agents.rule_based import RuleBasedAgent


KUHN_CARD_NAMES = {"0": "Jack", "1": "Queen", "2": "King"}

ACTION_NAMES_NO_BET = {0: "Pass/check", 1: "Bet"}
ACTION_NAMES_FACING_BET = {0: "Pass/fold", 1: "Call"}

ALL_BOTS = ["random", "always_call", "always_fold", "rule_based", "ev_heuristic"]


def build_bot(name: str, seed: int):
    bots = {
        "random": RandomAgent(seed=10_000 + seed),
        "always_call": AlwaysCallAgent(),
        "always_fold": AlwaysFoldAgent(),
        "rule_based": RuleBasedAgent(),
        "ev_heuristic": EVHeuristicAgent(seed=20_000 + seed),
    }
    if name not in bots:
        raise ValueError(f"Unknown bot {name}. Choose from: {sorted(bots)}")
    return bots[name]


def sample_chance_action(state, rng: np.random.Generator) -> int:
    outcomes = state.chance_outcomes()
    actions, probs = zip(*outcomes)
    return int(rng.choice(actions, p=np.array(probs, dtype=float)))


def sample_mystery_opponents(seed: int, n: int, available_bots: list[str]) -> list[str]:
    """Sample n bot names from the available bot pool.

    Sampling is reproducible because it uses the demo seed.
    If n <= number of bots, sampling is without replacement.
    If n > number of bots, sampling uses replacement.
    """
    rng = np.random.default_rng(seed)
    replace = n > len(available_bots)
    return list(rng.choice(available_bots, size=n, replace=replace))


def public_history_from_info(info_state: str) -> str:
    """For Kuhn info states like '1pb', return 'pb'."""
    return "".join(ch for ch in info_state if not ch.isdigit())


def private_card_from_info(info_state: str) -> str:
    """For Kuhn info states like '1pb', return 'Queen'."""
    for ch in info_state:
        if ch.isdigit():
            return KUHN_CARD_NAMES.get(ch, f"card_id={ch}")
    return "unknown"


def is_facing_bet(info_state: str) -> bool:
    return public_history_from_info(info_state).endswith("b")


def readable_actions(legal: list[int], facing_bet: bool) -> list[str]:
    names = ACTION_NAMES_FACING_BET if facing_bet else ACTION_NAMES_NO_BET
    return [f"{a}: {names.get(a, f'action_{a}')}" for a in legal]


def prompt_reveal_choice(slot_id: int) -> bool:
    """Ask once, before the first hand against a sampled bot, whether to reveal identity."""
    print("\n" + "-" * 80)
    print(f"Mystery opponent #{slot_id} has been sampled from the five Week 1 bots.")
    print("Available bot pool: random, always_call, always_fold, rule_based, ev_heuristic")
    print("The bot identity is hidden by default.")
    raw = input("Type 'reveal' to reveal the bot identity now, or press Enter to keep it hidden: ")
    return raw.strip().lower() == "reveal"


def prompt_human_action(state, player: int) -> int:
    info = state.information_state_string(player)
    legal = state.legal_actions()
    facing_bet = is_facing_bet(info)

    print("\nYOUR TURN")
    print(f"Your player id: P{player}")
    print(f"Your private card: {private_card_from_info(info)}")
    print(f"Public action history: {public_history_from_info(info) or '(none yet)'}")
    print(f"Legal actions: {readable_actions(legal, facing_bet)}")
    print("Note: action 0 is OpenSpiel 'p'; action 1 is OpenSpiel 'b'.")
    print("      Depending on context, p means check/fold and b means bet/call.")

    while True:
        raw = input(f"Choose action {legal}: ").strip()
        try:
            action = int(raw)
        except ValueError:
            print("Please enter an integer action id.")
            continue

        if action in legal:
            return action

        print(f"Illegal action {action}. Legal actions are {legal}.")


def play_hand_hidden(
    game,
    human_player: int,
    bot,
    real_bot_name: str,
    revealed: bool,
    deal_seed: int,
    log_lines: list[str],
) -> np.ndarray:
    """Play one hand without revealing the bot's private card.

    The bot name is shown only if the user chose 'reveal' before the first hand
    against this sampled opponent.
    """
    rng = np.random.default_rng(deal_seed)
    state = game.new_initial_state()
    display_bot_name = real_bot_name if revealed else "mystery_bot"

    log_lines.append(
        f"New hidden-information hand: human=P{human_player}, "
        f"bot=P{1-human_player}, bot_name={display_bot_name}, deal_seed={deal_seed}"
    )

    print("\n" + "=" * 80)
    print(f"New hand: you are Player {human_player}; opponent is {display_bot_name} as Player {1-human_player}")
    print("=" * 80)
    print("Cards are dealt by OpenSpiel chance nodes. The opponent's private card is hidden.")

    while not state.is_terminal():
        if state.is_chance_node():
            action = sample_chance_action(state, rng)
            state.apply_action(action)
            # Do not print the chance action: those are private card deals.
            log_lines.append("Chance node applied one hidden card-deal action.")
            continue

        player = state.current_player()

        if player == human_player:
            action = prompt_human_action(state, player)
            log_lines.append(
                f"Human P{player}: info_state={state.information_state_string(player)}, "
                f"legal={state.legal_actions()}, chose_action={action}"
            )
            state.apply_action(action)
        else:
            legal = state.legal_actions()
            action = int(bot.act(state))
            if action not in legal:
                raise ValueError(f"Bot chose illegal action {action}; legal={legal}")

            info = state.information_state_string(player)
            facing_bet = is_facing_bet(info)
            action_label = dict(item.split(": ", 1) for item in readable_actions(legal, facing_bet)).get(
                str(action), str(action)
            )

            print(f"\nOpponent ({display_bot_name}) acts: action {action} ({action_label})")
            log_lines.append(
                f"Bot {display_bot_name} P{player}: info_state=HIDDEN_FROM_HUMAN, "
                f"legal={legal}, chose_action={action}"
            )
            state.apply_action(action)

    returns = np.array(state.returns(), dtype=float)

    print("\nHAND OVER")
    print(f"Your payoff: {returns[human_player]}")
    print(f"Opponent payoff: {returns[1 - human_player]}")
    print("Full terminal state is not shown during play to preserve hidden information.")

    log_lines.append(f"Terminal returns: human={returns[human_player]}, bot={returns[1-human_player]}")
    log_lines.append("-" * 80)
    return returns


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", default="kuhn_poker", choices=["kuhn_poker"])
    parser.add_argument(
        "--num-mystery-bots",
        type=int,
        default=2,
        help="How many randomly sampled bots to play against.",
    )
    parser.add_argument(
        "--available-bots",
        nargs="+",
        default=ALL_BOTS,
        choices=ALL_BOTS,
        help="Pool from which mystery opponents are sampled.",
    )
    parser.add_argument("--pairs-per-opponent", type=int, default=1)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", default="results/logs/human_vs_mystery_bots_demo.txt")
    args = parser.parse_args()

    game = pyspiel.load_game(args.game)
    mystery_opponents = sample_mystery_opponents(
        seed=args.seed,
        n=args.num_mystery_bots,
        available_bots=args.available_bots,
    )

    log_lines: list[str] = []
    total_payoff = 0.0

    log_lines.append("Human vs randomly sampled mystery bots demo")
    log_lines.append(f"Game: {args.game}")
    log_lines.append(f"Available bot pool: {args.available_bots}")
    log_lines.append(f"Sampled bot identities hidden unless revealed by user.")
    log_lines.append(f"Pairs per opponent: {args.pairs_per_opponent}")
    log_lines.append(f"Seed: {args.seed}")
    log_lines.append("=" * 80)

    print("\nHuman vs mystery bots demo")
    print(f"Game: {args.game}")
    print(f"Number of mystery opponents sampled: {args.num_mystery_bots}")
    print(f"Pairs per opponent: {args.pairs_per_opponent}")
    print("Each duplicate pair has two hands: you play once as P0 and once as P1.")

    for opp_idx, real_bot_name in enumerate(mystery_opponents, start=1):
        revealed = prompt_reveal_choice(slot_id=opp_idx)
        if revealed:
            print(f"Revealed: mystery opponent #{opp_idx} is {real_bot_name}.")
            log_lines.append(f"Mystery opponent #{opp_idx}: REVEALED as {real_bot_name}")
        else:
            print(f"Opponent #{opp_idx} remains hidden as mystery_bot.")
            log_lines.append(f"Mystery opponent #{opp_idx}: HIDDEN")

        for pair in range(args.pairs_per_opponent):
            # One duplicate pair: human plays each seat once under the same base deal seed.
            deal_seed = args.seed * 1_000_000 + (opp_idx - 1) * 10_000 + pair

            bot_a = build_bot(real_bot_name, seed=args.seed + opp_idx + pair)
            returns_a = play_hand_hidden(
                game=game,
                human_player=0,
                bot=bot_a,
                real_bot_name=real_bot_name,
                revealed=revealed,
                deal_seed=deal_seed,
                log_lines=log_lines,
            )
            total_payoff += returns_a[0]

            bot_b = build_bot(real_bot_name, seed=args.seed + opp_idx + pair)
            returns_b = play_hand_hidden(
                game=game,
                human_player=1,
                bot=bot_b,
                real_bot_name=real_bot_name,
                revealed=revealed,
                deal_seed=deal_seed,
                log_lines=log_lines,
            )
            total_payoff += returns_b[1]

    print("\n" + "=" * 80)
    print(f"Demo complete. Total human payoff over all hands: {total_payoff}")
    print("=" * 80)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(log_lines), encoding="utf-8")
    print(f"Saved non-spoiler transcript to: {out}")


if __name__ == "__main__":
    main()
