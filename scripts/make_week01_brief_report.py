from __future__ import annotations

from datetime import datetime
from pathlib import Path
import subprocess
import pandas as pd


TOURNAMENT_CSV = Path("results/tables/exp01_baseline_tournament.csv")
SUMMARY_CSV = Path("results/tables/exp01_baseline_summary.csv")
REPORT_PATH = Path("reports/weekly/week01.md")


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "not-recorded"


def clean_number(x, digits: int = 4) -> str:
    if pd.isna(x):
        return ""
    try:
        x = float(x)
    except Exception:
        return str(x)
    if abs(x) < 0.00005:
        x = 0.0
    return f"{x:.{digits}f}"


def build_summary() -> pd.DataFrame:
    """Read baseline summary if it exists; otherwise generate it from tournament CSV."""
    if SUMMARY_CSV.exists():
        summary = pd.read_csv(SUMMARY_CSV)
    elif TOURNAMENT_CSV.exists():
        df = pd.read_csv(TOURNAMENT_CSV)
        summary = (
            df.groupby(["game", "agent_a", "agent_b"], as_index=False)
            .agg(
                mean_payoff=("mean_payoff_to_a", "mean"),
                avg_ci_low=("ci_low", "mean"),
                avg_ci_high=("ci_high", "mean"),
                avg_win_rate=("win_rate_a", "mean"),
                avg_std=("std", "mean"),
            )
        )
        SUMMARY_CSV.parent.mkdir(parents=True, exist_ok=True)
        summary.to_csv(SUMMARY_CSV, index=False)
    else:
        raise FileNotFoundError(
            "Could not find results/tables/exp01_baseline_summary.csv or "
            "results/tables/exp01_baseline_tournament.csv. Run the baseline tournament first."
        )

    # Normalize column names from older/newer summary scripts.
    rename_map = {
        "Mean payoff to A": "mean_payoff",
        "95% CI low": "avg_ci_low",
        "95% CI high": "avg_ci_high",
        "Avg win rate A": "avg_win_rate",
    }
    summary = summary.rename(columns=rename_map)

    required = {"game", "agent_a", "agent_b", "mean_payoff"}
    missing = required - set(summary.columns)
    if missing:
        raise ValueError(f"Summary CSV is missing columns: {sorted(missing)}")

    for optional in ["avg_ci_low", "avg_ci_high", "avg_win_rate", "avg_std"]:
        if optional not in summary.columns:
            summary[optional] = pd.NA

    return summary.sort_values("mean_payoff", ascending=False).reset_index(drop=True)


def markdown_results_table(summary: pd.DataFrame) -> str:
    view = summary.copy()
    view = view.rename(
        columns={
            "game": "Game",
            "agent_a": "Agent A",
            "agent_b": "Agent B",
            "mean_payoff": "Mean payoff to A",
            "avg_ci_low": "CI low",
            "avg_ci_high": "CI high",
            "avg_win_rate": "Win rate A",
        }
    )

    keep = ["Agent A", "Agent B", "Mean payoff to A", "CI low", "CI high", "Win rate A"]
    view = view[keep]

    for col in ["Mean payoff to A", "CI low", "CI high", "Win rate A"]:
        view[col] = view[col].apply(clean_number)

    return view.to_markdown(index=False)


def row(summary: pd.DataFrame, a: str, b: str) -> pd.Series | None:
    m = summary[(summary["agent_a"] == a) & (summary["agent_b"] == b)]
    if len(m) == 0:
        return None
    return m.iloc[0]


def fmt_row(summary: pd.DataFrame, a: str, b: str) -> str:
    r = row(summary, a, b)
    if r is None:
        return "`not found`"
    return clean_number(r["mean_payoff"])


def main() -> None:
    summary = build_summary()

    # Raw run metadata
    if TOURNAMENT_CSV.exists():
        raw = pd.read_csv(TOURNAMENT_CSV)
        seeds = sorted(int(x) for x in raw["seed"].unique()) if "seed" in raw else []
        n_pairs = sorted(int(x) for x in raw["n_duplicate_pairs"].unique()) if "n_duplicate_pairs" in raw else []
        games = sorted(str(x) for x in raw["game"].unique()) if "game" in raw else ["kuhn_poker"]
        rows = len(raw)
    else:
        seeds, n_pairs, games, rows = [], [], ["kuhn_poker"], len(summary)

    best = summary.iloc[0]
    worst = summary.iloc[-1]

    report = f"""# Week 1 Report — Baseline Poker Bots on Kuhn Poker

**Date generated:** {datetime.now().strftime("%Y-%m-%d %H:%M")}  
**Git commit:** `{git_commit()}`  
**Experiment:** `exp01_baseline_tournament.py`  
**Game:** `{", ".join(games)}`  

## 1. Objective

The objective of Week 1 was to build a working experimental pipeline for the PokerAI summer project before moving to regret minimization. Instead of starting directly with CFR/MCCFR, this week focused on three foundations:

1. loading Kuhn Poker from OpenSpiel,
2. implementing simple baseline agents,
3. evaluating those agents through a reproducible tournament.

This gives us a sanity-checked environment where future CFR, CFR+, and MCCFR agents can be compared against clear lower baselines.

## 2. What Was Achieved

By the end of Week 1, the project had the following working components:

- a Windows-compatible Python virtual environment,
- an OpenSpiel `kuhn_poker` setup,
- five baseline agents: `random`, `always_call`, `always_fold`, `rule_based`, and `ev_heuristic`,
- a duplicate-pair tournament evaluator,
- CSV result logging under `results/tables/`,
- a one-hand OpenSpiel observer script for explaining state transitions,
- Git/GitHub version control for code, reports, and slides.

The main technical achievement is that the project now has a complete loop:

```text
OpenSpiel game -> bot action -> state transition -> payoff -> result table
```

## 3. Experimental Setup

The Week 1 tournament was a round-robin among the five baseline agents. With five agents, there are:

```text
5 choose 2 = 10 pairwise matchups
```

For each matchup, the evaluator used duplicate-pair evaluation. In one duplicate pair, the same card-deal seed is used twice:

1. Agent A plays as Player 0 and Agent B plays as Player 1.
2. The seats are swapped: Agent B plays as Player 0 and Agent A plays as Player 1.

The payoff to Agent A is then averaged across the two hands. This reduces card-luck and seat-position variance.

**Run metadata**

- Result rows in raw tournament file: `{rows}`
- Experimental seeds: `{seeds if seeds else "not recorded"}`
- Duplicate pairs per matchup per seed: `{n_pairs if n_pairs else "not recorded"}`
- Actual hands per matchup per seed: `2 × n_duplicate_pairs`

## 4. Main Metric

The headline metric is:

```text
mean_payoff_to_a
```

This is the average chip payoff to Agent A. It is better than win rate because poker hands can have different payoff sizes. A bot can win many small pots and still lose money overall if it loses larger pots.

Interpretation:

- positive mean payoff: Agent A beats Agent B on average,
- negative mean payoff: Agent A loses to Agent B on average,
- near zero: roughly even under this evaluation.

## 5. Results

{markdown_results_table(summary)}

## 6. Key Observations

### 6.1 Strongest and weakest rows

The strongest Agent-A result was:

```text
{best["agent_a"]} vs {best["agent_b"]}: mean payoff to A = {clean_number(best["mean_payoff"])}
```

The weakest Agent-A result was:

```text
{worst["agent_a"]} vs {worst["agent_b"]}: mean payoff to A = {clean_number(worst["mean_payoff"])}
```

### 6.2 Degenerate strategies behave as expected

`always_call` strongly beats `always_fold` with mean payoff `{fmt_row(summary, "always_call", "always_fold")}`. This is expected because an always-folding/passive strategy gives up too much value.

`random` also beats `always_fold` with mean payoff `{fmt_row(summary, "random", "always_fold")}`, confirming that an active strategy can exploit an overly passive one.

### 6.3 Rule-based bot improved after adding domain logic

The updated rule-based bot uses card strength and whether it is facing a bet:

- King: bet/call,
- Queen: check/pass if no bet is pending, call if facing a bet,
- Jack: check/fold.

This is why `always_call` now loses to `rule_based` with mean payoff to always-call of `{fmt_row(summary, "always_call", "rule_based")}`. The rule-based bot avoids some bad calls and punishes over-aggressive play.

### 6.4 EV heuristic remains the strongest simple baseline

The row `rule_based vs ev_heuristic` has mean payoff `{fmt_row(summary, "rule_based", "ev_heuristic")}`. Since this is negative, the rule-based bot loses to the EV-inspired heuristic. This is consistent with the intended ladder: the EV heuristic is supposed to be stronger than simple hand-coded rules, but still weaker than future CFR-style agents.

### 6.5 Why `always_fold vs rule_based` can be exactly zero

The row `always_fold vs rule_based` is `{fmt_row(summary, "always_fold", "rule_based")}`. This can happen because results are reported after duplicate-pair averaging. Individual hands can be won or lost, but after swapping seats on the same deal, the payoff may cancel exactly for this simple matchup.

## 7. Current Interpretation

The Week 1 results are qualitatively sensible:

- random play is weak but not completely inactive,
- always-fold is exploitable,
- always-call is exploitable by more selective strategies,
- rule-based play improves after adding basic poker logic,
- EV-inspired play is the strongest simple Week 1 baseline.

This means the evaluation pipeline is working and can now support more serious algorithms.

## 8. Next Week

Week 2 will move from fixed baseline agents to regret minimization. The next tasks are:

1. implement regret matching on Rock-Paper-Scissors,
2. track average strategy convergence,
3. plot average regret over time,
4. connect regret matching to Counterfactual Regret Minimization.

This prepares the project for vanilla CFR on Kuhn Poker in Week 3.

## 9. Final Week 1 Status

Week 1 is complete. The repo now has a working OpenSpiel environment, baseline bots, reproducible tournament evaluation, generated result tables, explanatory logs, reports, and presentation material.
"""

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote brief Week 1 report to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
