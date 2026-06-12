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
#
# This is a zero-sum game, so +1 for the row player implies -1 for
# the column player.
PAYOFF_MATRIX = np.array(
    [
        [0.0, -1.0, 1.0],
        [1.0, 0.0, -1.0],
        [-1.0, 1.0, 0.0],
    ],
    dtype=np.float64,
)


def _validate_action(action: int) -> None:
    """Raise an error if action is not a valid RPS action."""
    if action not in (ROCK, PAPER, SCISSORS):
        raise ValueError(f"Invalid action {action}. Choose 0=rock, 1=paper, or 2=scissors.")


def action_name(action: int) -> str:
    """Return the readable name of an RPS action."""
    _validate_action(action)
    return ACTIONS[action]


def payoff(row_action: int, col_action: int) -> float:
    """
    Return payoff to the row player.

    row_action is the action chosen by the player whose payoff we want.
    col_action is the opponent's action.
    """
    _validate_action(row_action)
    _validate_action(col_action)

    return float(PAYOFF_MATRIX[row_action, col_action])


def action_utilities_against(opponent_action: int) -> np.ndarray:
    """
    Return utility for each possible action against a fixed opponent action.

    Example:
        If opponent played Paper, this returns:
        [utility(Rock, Paper), utility(Paper, Paper), utility(Scissors, Paper)]
        = [-1, 0, +1]
    """
    _validate_action(opponent_action)
    return PAYOFF_MATRIX[:, opponent_action].copy()