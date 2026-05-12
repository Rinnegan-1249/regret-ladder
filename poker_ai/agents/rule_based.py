from __future__ import annotations

import re

from poker_ai.agents.base import Agent


def _private_card_from_info_state(info_state: str) -> int | None:
    """Best-effort parser for Kuhn/Leduc information state strings.

    OpenSpiel information-state strings differ slightly by game/version. For Week 1,
    this simple parser is enough for a heuristic baseline: it extracts the first integer
    visible in the information state, which is usually the player's private card.
    """
    match = re.search(r"\d+", info_state)
    return int(match.group(0)) if match else None


class RuleBasedAgent(Agent):
    """Tiny tight-aggressive baseline.

    Heuristic:
    - With a high private card, choose aggressive/call action if legal.
    - With a low private card, choose passive/fold action if legal.
    - With middle cards, lean passive unless already facing action.

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

        # Kuhn cards are usually 0,1,2. Leduc has a slightly larger action space,
        # but this still gives a reasonable baseline.
        if card >= 2:
            return aggressive
        return passive
