from __future__ import annotations

from itertools import combinations
from typing import Dict, Iterable

import numpy as np
import pandas as pd
import pyspiel
from tqdm import tqdm

from poker_ai.agents.base import Agent
from poker_ai.evaluation.stats import summarize_payoffs


def play_one_hand(game, agents: list[Agent], deal_seed: int) -> np.ndarray:
    """Play one OpenSpiel hand using a deterministic chance RNG.

    The same `deal_seed` can be reused after swapping seats to create duplicate-pair
    evaluation and reduce card-luck variance.
    """
    rng = np.random.default_rng(deal_seed)
    state = game.new_initial_state()

    while not state.is_terminal():
        if state.is_chance_node():
            outcomes = state.chance_outcomes()
            actions, probs = zip(*outcomes)
            action = int(rng.choice(actions, p=np.array(probs, dtype=float)))
            state.apply_action(action)
        else:
            player = state.current_player()
            action = int(agents[player].act(state))
            legal = state.legal_actions()
            if action not in legal:
                raise ValueError(
                    f"Agent {agents[player].name} chose illegal action {action}; legal={legal}"
                )
            state.apply_action(action)

    return np.array(state.returns(), dtype=float)


def duplicate_match(game, agent_a: Agent, agent_b: Agent, n_pairs: int, base_seed: int) -> np.ndarray:
    """Evaluate A vs B with duplicate paired deals.

    For each deal, play A as player 0 and B as player 1; then swap seats with the
    exact same chance seed. Return payoff to agent A averaged across the two seats.
    """
    payoffs_a: list[float] = []
    for k in range(n_pairs):
        deal_seed = base_seed + k
        u_ab = play_one_hand(game, [agent_a, agent_b], deal_seed=deal_seed)
        u_ba = play_one_hand(game, [agent_b, agent_a], deal_seed=deal_seed)
        payoff_to_a = 0.5 * (u_ab[0] + u_ba[1])
        payoffs_a.append(float(payoff_to_a))
    return np.array(payoffs_a, dtype=float)


def round_robin(
    game_name: str,
    agents: Dict[str, Agent],
    n_pairs: int,
    seeds: Iterable[int],
) -> pd.DataFrame:
    game = pyspiel.load_game(game_name)
    rows = []
    pairs = list(combinations(agents.items(), 2))

    for seed in seeds:
        for (name_a, agent_a), (name_b, agent_b) in tqdm(pairs, desc=f"seed={seed}"):
            payoffs = duplicate_match(
                game=game,
                agent_a=agent_a,
                agent_b=agent_b,
                n_pairs=n_pairs,
                base_seed=int(seed) * 1_000_000,
            )
            s = summarize_payoffs(payoffs)
            rows.append(
                {
                    "game": game_name,
                    "seed": seed,
                    "agent_a": name_a,
                    "agent_b": name_b,
                    "n_duplicate_pairs": s.n,
                    "mean_payoff_to_a": s.mean,
                    "ci_low": s.ci_low,
                    "ci_high": s.ci_high,
                    "std": s.std,
                    "win_rate_a": s.win_rate,
                    "p_value_vs_zero": s.p_value_vs_zero,
                }
            )
    return pd.DataFrame(rows)
