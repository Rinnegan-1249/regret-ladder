# Week 1 Report — Baseline Poker Bots on Kuhn Poker

**Date generated:** 2026-05-15 13:51  
**Git commit:** `873ec24`  
**Experiment:** `exp01_baseline_tournament.py`  
**Game:** `kuhn_poker`  

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

- Result rows in raw tournament file: `50`
- Experimental seeds: `[0, 1, 2, 3, 4]`
- Duplicate pairs per matchup per seed: `[10000]`
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

| Agent A     | Agent B      |   Mean payoff to A |   CI low |   CI high |   Win rate A |
|:------------|:-------------|-------------------:|---------:|----------:|-------------:|
| always_call | always_fold  |             1      |   1      |    1      |       1      |
| random      | always_fold  |             0.501  |   0.4912 |    0.5108 |       0.501  |
| always_fold | rule_based   |             0      |   0      |    0      |       0      |
| rule_based  | ev_heuristic |            -0.0896 |  -0.0934 |   -0.0859 |       0      |
| always_fold | ev_heuristic |            -0.1167 |  -0.123  |   -0.1104 |       0      |
| always_call | ev_heuristic |            -0.1522 |  -0.1634 |   -0.1411 |       0.1804 |
| random      | ev_heuristic |            -0.1614 |  -0.1714 |   -0.1514 |       0.1255 |
| random      | rule_based   |            -0.2111 |  -0.2171 |   -0.2052 |       0.0612 |
| always_call | rule_based   |            -0.334  |  -0.3386 |   -0.3293 |       0      |
| random      | always_call  |            -0.382  |  -0.3974 |   -0.3667 |       0.2485 |

## 6. Key Observations

### 6.1 Strongest and weakest rows

The strongest Agent-A result was:

```text
always_call vs always_fold: mean payoff to A = 1.0000
```

The weakest Agent-A result was:

```text
random vs always_call: mean payoff to A = -0.3820
```

### 6.2 Degenerate strategies behave as expected

`always_call` strongly beats `always_fold` with mean payoff `1.0000`. This is expected because an always-folding/passive strategy gives up too much value.

`random` also beats `always_fold` with mean payoff `0.5010`, confirming that an active strategy can exploit an overly passive one.

### 6.3 Rule-based bot improved after adding domain logic

The updated rule-based bot uses card strength and whether it is facing a bet:

- King: bet/call,
- Queen: check/pass if no bet is pending, call if facing a bet,
- Jack: check/fold.

This is why `always_call` now loses to `rule_based` with mean payoff to always-call of `-0.3340`. The rule-based bot avoids some bad calls and punishes over-aggressive play.

### 6.4 EV heuristic remains the strongest simple baseline

The row `rule_based vs ev_heuristic` has mean payoff `-0.0896`. Since this is negative, the rule-based bot loses to the EV-inspired heuristic. This is consistent with the intended ladder: the EV heuristic is supposed to be stronger than simple hand-coded rules, but still weaker than future CFR-style agents.

### 6.5 Why `always_fold vs rule_based` can be exactly zero

The row `always_fold vs rule_based` is `0.0000`. This can happen because results are reported after duplicate-pair averaging. Individual hands can be won or lost, but after swapping seats on the same deal, the payoff may cancel exactly for this simple matchup.

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
