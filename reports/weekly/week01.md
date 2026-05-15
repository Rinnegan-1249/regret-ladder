# Week 1 Report ? PokerAI Baseline Environment and Tournament

**Date:** 2026-05-15 11:27  
**Git commit:** `3589f6f`  
**Experiment:** `exp01_baseline_tournament.py`  
**Game:** `kuhn_poker`  

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

- Number of result rows: `50`
- Seeds used: `[np.int64(0), np.int64(1), np.int64(2), np.int64(3), np.int64(4)]`
- Duplicate pairs per seed: `[np.int64(10000)]`
- Agents: `always_call, always_fold, ev_heuristic, random, rule_based`

A seed fixes the random number generator used for card deals and stochastic decisions. Running seeds `[np.int64(0), np.int64(1), np.int64(2), np.int64(3), np.int64(4)]` gives multiple independent repetitions of the same experiment, reducing dependence on a single lucky or unlucky run.

The main metric is **mean payoff to Agent A**.

- Positive value: Agent A beats Agent B on average.
- Negative value: Agent A loses to Agent B on average.
- Near zero: roughly even matchup.

## 5. Results

| Game       | Agent A     | Agent B      | Seeds     |   N per seed |   Mean payoff to A |   95% CI low |   95% CI high |   Avg win rate A |
|:-----------|:------------|:-------------|:----------|-------------:|-------------------:|-------------:|--------------:|-----------------:|
| kuhn_poker | always_call | always_fold  | 0,1,2,3,4 |        10000 |             1      |       1      |        1      |           1      |
| kuhn_poker | random      | always_fold  | 0,1,2,3,4 |        10000 |             0.501  |       0.4963 |        0.5058 |           0.501  |
| kuhn_poker | always_fold | rule_based   | 0,1,2,3,4 |        10000 |             0      |       0      |        0      |           0      |
| kuhn_poker | rule_based  | ev_heuristic | 0,1,2,3,4 |        10000 |            -0.0896 |      -0.091  |       -0.0882 |           0      |
| kuhn_poker | always_fold | ev_heuristic | 0,1,2,3,4 |        10000 |            -0.1167 |      -0.119  |       -0.1143 |           0      |
| kuhn_poker | always_call | ev_heuristic | 0,1,2,3,4 |        10000 |            -0.1522 |      -0.1557 |       -0.1488 |           0.1804 |
| kuhn_poker | random      | ev_heuristic | 0,1,2,3,4 |        10000 |            -0.1614 |      -0.1656 |       -0.1571 |           0.1255 |
| kuhn_poker | random      | rule_based   | 0,1,2,3,4 |        10000 |            -0.2111 |      -0.2138 |       -0.2084 |           0.0612 |
| kuhn_poker | always_call | rule_based   | 0,1,2,3,4 |        10000 |            -0.334  |      -0.3358 |       -0.3321 |           0      |
| kuhn_poker | random      | always_call  | 0,1,2,3,4 |        10000 |            -0.382  |      -0.3936 |       -0.3705 |           0.2485 |

## 6. Main Observations

The strongest observed matchup for Agent A was:

> **always_call vs always_fold**, with mean payoff to A = **1.0**.

The weakest observed matchup for Agent A was:

> **random vs always_call**, with mean payoff to A = **-0.382**.

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

