from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Iterable
import inspect
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from tqdm import tqdm


def _child(state, action: int):
    child = state.clone()
    child.apply_action(int(action))
    return child

def call_agent_act(agent, state, rng):
    """
    Supports both old Week 1 agents:
        act(state)

    and newer Week 3 agents:
        act(state, rng)
    """
    sig = inspect.signature(agent.act)
    n_params = len(sig.parameters)

    # Bound method: self is already removed.
    if n_params == 1:
        return agent.act(state)

    return agent.act(state, rng)
def play_one_hand(game, agents, rng: np.random.Generator):
    state = game.new_initial_state()
    while not state.is_terminal():
        if state.is_chance_node():
            outcomes = state.chance_outcomes()
            actions = [int(a) for a, _ in outcomes]
            probs = np.asarray([p for _, p in outcomes], dtype=np.float64)
            probs = probs / probs.sum()
            action = int(rng.choice(actions, p=probs))
            state.apply_action(action)
        else:
            player = state.current_player()
            action = call_agent_act(agents[player], state, rng)
            if action not in state.legal_actions():
                raise ValueError(f"Illegal action {action}; legal={state.legal_actions()}; agent={agents[player].name}")
            state.apply_action(int(action))
    return np.asarray(state.returns(), dtype=np.float64)


def duplicate_match(game, agent_a, agent_b, n_pairs: int, seed: int) -> np.ndarray:
    """Returns duplicate-paired payoff samples from A's perspective."""
    payoffs = np.zeros(n_pairs, dtype=np.float64)
    for k in range(n_pairs):
        # Same seed gives same chance path; agents are swapped in the second hand.
        rng1 = np.random.default_rng(seed * 1_000_000 + k)
        rng2 = np.random.default_rng(seed * 1_000_000 + k)
        u_ab = play_one_hand(game, [agent_a, agent_b], rng1)
        u_ba = play_one_hand(game, [agent_b, agent_a], rng2)
        payoffs[k] = 0.5 * (u_ab[0] + u_ba[1])
    return payoffs


@dataclass
class MatchResult:
    agent_a: str
    agent_b: str
    mean: float
    ci_low: float
    ci_high: float
    p_value: float
    n: int
    seeds: str


def summarize_samples(agent_a: str, agent_b: str, samples: np.ndarray, seeds: Iterable[int]) -> MatchResult:
    mean = float(samples.mean())
    if len(samples) > 1:
        sem = float(samples.std(ddof=1) / np.sqrt(len(samples)))
        ci_low = mean - 1.96 * sem
        ci_high = mean + 1.96 * sem
        p_value = float(stats.ttest_1samp(samples, 0.0).pvalue)
    else:
        ci_low = ci_high = mean
        p_value = 1.0
    return MatchResult(agent_a, agent_b, mean, ci_low, ci_high, p_value, len(samples), ",".join(map(str, seeds)))


def run_round_robin(game, agents, n_pairs: int, seeds: list[int], show_progress: bool = True):
    names = [a.name for a in agents]
    matrix = pd.DataFrame(np.zeros((len(agents), len(agents))), index=names, columns=names)
    long_rows: list[MatchResult] = []

    pairs = list(combinations(range(len(agents)), 2))
    iterator = tqdm(pairs, desc="round-robin") if show_progress else pairs
    for i, j in iterator:
        all_samples = []
        for seed in seeds:
            all_samples.append(duplicate_match(game, agents[i], agents[j], n_pairs=n_pairs, seed=seed))
        samples = np.concatenate(all_samples)
        result = summarize_samples(names[i], names[j], samples, seeds)
        matrix.iloc[i, j] = result.mean
        matrix.iloc[j, i] = -result.mean
        long_rows.append(result)
        long_rows.append(summarize_samples(names[j], names[i], -samples, seeds))

    long_df = pd.DataFrame([r.__dict__ for r in long_rows])
    return matrix, long_df


def add_average_and_max(matrix: pd.DataFrame) -> pd.DataFrame:
    out = matrix.copy()
    n = len(matrix)
    out["Average"] = [
        (out.iloc[i, :n].sum() - out.iloc[i, i]) / (n - 1)
        for i in range(n)
    ]
    max_row = list(out.iloc[:n, :n].max(axis=0).values) + [np.nan]
    out.loc["Max"] = max_row
    return out


def save_paper_style_table(matrix_with_avg: pd.DataFrame, path: str | Path, title: str):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rounded = matrix_with_avg.copy()
    for col in rounded.columns:
        rounded[col] = rounded[col].map(lambda x: "" if pd.isna(x) else f"{x:.3f}")

    fig_w = max(10, 1.25 * len(rounded.columns))
    fig_h = max(4, 0.5 * len(rounded.index) + 1.5)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.axis("off")
    ax.set_title(title, pad=14)

    table = ax.table(
        cellText=rounded.values,
        rowLabels=rounded.index,
        colLabels=rounded.columns,
        cellLoc="center",
        rowLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.0, 1.35)

    n_rows, n_cols = matrix_with_avg.shape
    for (r, c), cell in table.get_celld().items():
        if r == 0 or c == -1:
            cell.set_text_props(weight="bold")
            continue
        value = matrix_with_avg.iloc[r - 1, c]
        if pd.isna(value):
            continue
        # Light green for positive, light red for negative, white near zero.
        if value > 1e-9:
            cell.set_facecolor("#d8f5d1")
        elif value < -1e-9:
            cell.set_facecolor("#f7cccc")

    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
