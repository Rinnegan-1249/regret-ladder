from __future__ import annotations

import numpy as np

ACTIONS = ("rock", "paper", "scissors")

ROCK = 0
PAPER = 1
SCISSORS = 2

# Payoff matrix for the row player.
#
#           Opponent
#           R   P   S
# You R   [ 0, -1, +1]
#     P   [+1,  0, -1]
#     S   [-1, +1,  0]
#
# +1 means row player wins.
# -1 means row player loses.
#  0 means draw.
PAYOFF_MATRIX = np.array(
    [
        [0.0, -1.0, 1.0],
        [1.0, 0.0, -1.0],
        [-1.0, 1.0, 0.0],
    ],
    dtype=np.float64,
)


def action_name(action: int) -> str:
    """Return the readable name of an RPS action."""
    return ACTIONS[action]


def payoff(row_action: int, col_action: int) -> float:
    """Return payoff to the row player."""
    return float(PAYOFF_MATRIX[row_action, col_action])


def action_utilities_against(opponent_action: int) -> np.ndarray:
    """
    Return utility for each possible action against a fixed opponent action.

    Example:
        If opponent played Paper, this returns:
        [utility(Rock, Paper), utility(Paper, Paper), utility(Scissors, Paper)]
        = [-1, 0, +1]
    """
    return PAYOFF_MATRIX[:, opponent_action].copy()