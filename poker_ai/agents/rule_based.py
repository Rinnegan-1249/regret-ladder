from __future__ import annotations

import re

from poker_ai.agents.base import Agent


def _private_card_from_info_state(info_state: str) -> int | None:
    """Extract the first integer visible in the information state.

    In Kuhn Poker, this is the player's private card:
    0 = Jack, 1 = Queen, 2 = King.
    """
    match = re.search(r"\d+", info_state)
    return int(match.group(0)) if match else None


def _public_action_history(info_state: str) -> str:
    """Remove the private card digits and keep only public action letters.

    Examples:
    '1'   -> ''
    '0p'  -> 'p'
    '1pb' -> 'pb'
    """
    return re.sub(r"\d+", "", info_state)


def _facing_bet(info_state: str) -> bool:
    """Returns True if the player is currently responding to a bet.

    In Kuhn Poker, if the public action history ends with 'b',
    the current player is facing an outstanding bet.
    """
    public_history = _public_action_history(info_state)
    return public_history.endswith("b")


class RuleBasedAgent(Agent):
    """Tiny tight-aggressive baseline.

    Heuristic:
    - With King, bet/call aggressively.
    - With Jack, check/fold passively.
    - With Queen, check/pass if no one has bet, but call if facing a bet.

    This is deliberately simple. Its job is to create a non-random baseline that CFR
    should later beat.
    """

    name = "rule_based_tight_aggressive"

    def act(self, state) -> int:
        player = state.current_player()
        info = state.information_state_string(player)
        card = _private_card_from_info_state(info)
        legal = state.legal_actions()

        passive = 0 if 0 in legal else int(legal[0])
        aggressive = 1 if 1 in legal else int(legal[-1])

        if card is None:
            return passive

        facing_bet = _facing_bet(info)

        if card >= 2:
            return aggressive

        if card <= 0:
            return passive

        if card == 1:
            return aggressive if facing_bet else passive

        return passive