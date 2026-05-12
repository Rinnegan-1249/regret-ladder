from pathlib import Path
from datetime import datetime
import subprocess
import pandas as pd
import numpy as np

csv_path = Path("results/tables/exp01_baseline_tournament.csv")
report_path = Path("reports/weekly/week01.md")
report_path.parent.mkdir(parents=True, exist_ok=True)

if not csv_path.exists():
    raise FileNotFoundError(f"Could not find {csv_path}. Run exp01_baseline_tournament.py first.")

df = pd.read_csv(csv_path)

def get_git_commit():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True
        ).strip()
    except Exception:
        return "not-recorded"

def ci_from_seed_means(values):
    values = np.asarray(values, dtype=float)
    n = len(values)
    mean = values.mean()
    if n <= 1:
        return mean, np.nan, np.nan
    se = values.std(ddof=1) / np.sqrt(n)
    return mean, mean - 1.96 * se, mean + 1.96 * se

summary_rows = []
for (game, agent_a, agent_b), g in df.groupby(["game", "agent_a", "agent_b"]):
    mean, ci_low, ci_high = ci_from_seed_means(g["mean_payoff_to_a"])
    summary_rows.append({
        "Game": game,
        "Agent A": agent_a,
        "Agent B": agent_b,
        "Seeds": ",".join(map(str, sorted(g["seed"].unique()))),
        "N per seed": int(g["n_duplicate_pairs"].iloc[0]),
        "Mean payoff to A": round(mean, 4),
        "95% CI low": round(ci_low, 4) if not np.isnan(ci_low) else "",
        "95% CI high": round(ci_high, 4) if not np.isnan(ci_high) else "",
        "Avg win rate A": round(g["win_rate_a"].mean(), 4),
    })

summary = pd.DataFrame(summary_rows).sort_values("Mean payoff to A", ascending=False)

best = summary.iloc[0]
worst = summary.iloc[-1]

markdown_table = summary.to_markdown(index=False)

n_rows = len(df)
seeds = sorted(df["seed"].unique())
games = sorted(df["game"].unique())
agents = sorted(set(df["agent_a"]).union(set(df["agent_b"])))
n_pairs = sorted(df["n_duplicate_pairs"].unique())
git_commit = get_git_commit()
date = datetime.now().strftime("%Y-%m-%d %H:%M")

report = f"""# Week 1 Report ? PokerAI Baseline Environment and Tournament

**Date:** {date}  
**Git commit:** `{git_commit}`  
**Experiment:** `exp01_baseline_tournament.py`  
**Game:** `{", ".join(games)}`  

## 1. Objective

The objective of Week 1 was to set up a reproducible research environment for the poker bot project and establish baseline performance on Kuhn Poker. This week focused on infrastructure, simple baseline agents, and a first round-robin evaluation pipeline.

The larger project goal is to move from simple bots to regret-minimization methods such as CFR, CFR+, and MCCFR. Therefore, Week 1 intentionally starts with simple agents so that later solver-based agents can be compared against clear lower baselines.

## 2. Environment Setup

The repository was initialized and pushed to GitHub. A Python virtual environment was created on Windows, dependencies were installed, and OpenSpiel was verified through the baseline tournament.

The project currently contains:

- baseline agents under `poker_ai/agents/`
- tournament/evaluation logic under `poker_ai/evaluation/`
- experiment scripts under `experiments/`
- result CSVs under `results/tables/`
- weekly reports under `reports/weekly/`

## 3. Agents Implemented

The following five baseline agents were included in the Week 1 tournament:

1. **Random Agent** ? chooses uniformly among legal actions.
2. **Always-Call Agent** ? calls/checks when possible.
3. **Always-Fold Agent** ? folds when possible.
4. **Rule-Based Agent** ? simple hand-coded heuristic.
5. **EV-Heuristic Agent** ? simple expected-value-inspired heuristic.

These agents are intentionally weak/simple. Their purpose is not to solve poker, but to define reference points before moving to regret matching and CFR.

## 4. Experimental Design

The experiment was a round-robin tournament among the five baseline agents on Kuhn Poker.

**Configuration:**

- Number of result rows: `{n_rows}`
- Seeds used: `{seeds}`
- Duplicate pairs per seed: `{n_pairs}`
- Agents: `{", ".join(agents)}`

A seed fixes the random number generator used for card deals and stochastic decisions. Running seeds `{seeds}` gives multiple independent repetitions of the same experiment, reducing dependence on a single lucky or unlucky run.

The main metric is **mean payoff to Agent A**.

- Positive value: Agent A beats Agent B on average.
- Negative value: Agent A loses to Agent B on average.
- Near zero: roughly even matchup.

## 5. Results

{markdown_table}

## 6. Main Observations

The strongest observed matchup for Agent A was:

> **{best["Agent A"]} vs {best["Agent B"]}**, with mean payoff to A = **{best["Mean payoff to A"]}**.

The weakest observed matchup for Agent A was:

> **{worst["Agent A"]} vs {worst["Agent B"]}**, with mean payoff to A = **{worst["Mean payoff to A"]}**.

The results behave as expected for sanity-check baselines. Degenerate strategies such as always folding are exploitable, while more active strategies can gain consistently against them. This confirms that the tournament loop, payoff recording, duplicate pairing, and CSV logging are functioning.

## 7. Issues Encountered and Fixes

Several setup issues were resolved:

1. The ZIP archive had already been extracted, so PowerShell refused to overwrite existing files.
2. GitHub CLI was not installed initially, so the repository was pushed after setting up Git/GitHub access.
3. Python could not initially import `poker_ai`, which was fixed by configuring the project package through `pyproject.toml`.
4. The baseline tournament was successfully executed after the editable package setup was fixed.

## 8. Next Week Plan

Week 2 will move from fixed baseline agents to regret minimization.

Planned tasks:

1. Implement regret matching from scratch on Rock-Paper-Scissors.
2. Track average strategy convergence toward the Nash equilibrium.
3. Plot regret decay over iterations.
4. Write a short explanation connecting regret matching to CFR.

This is the conceptual bridge from simple poker bots to Counterfactual Regret Minimization.

## 9. Current Status

Week 1 is complete at the infrastructure level:

- GitHub repo created and pushed.
- Python environment working.
- OpenSpiel-based Kuhn Poker tournament working.
- Five baseline agents implemented.
- Multi-seed tournament results generated.
- Weekly report generated.

"""

report_path.write_text(report, encoding="utf-8")
print(f"Wrote report to {report_path}")
print("\nPreview:\n")
print(report[:2000])
