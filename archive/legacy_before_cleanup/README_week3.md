# Week 3 Poker CFR Pipeline

This patch adds:

1. A from-scratch `VanillaCFR` implementation for Kuhn Poker.
2. An OpenSpiel `CFRSolver` reference baseline.
3. A paper-style cross-table among five baseline bots + our CFR + OpenSpiel CFR.
4. Convergence plot: exploitability vs iterations.

## Setup

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements_week3.txt
python -c "import pyspiel; g=pyspiel.load_game('kuhn_poker'); print(g.num_distinct_actions(), g.max_game_length())"
```

Expected smoke-test output: `2 4`.

## Commands

```bash
# 1) Validate our CFR against OpenSpiel
python scripts/validate_week3.py --game kuhn_poker --iters 1000

# 2) Produce convergence CSV + plot
python experiments/exp03_train_cfr.py --game kuhn_poker --iters 10000

# 3) Produce paper-style payoff cross-table
python experiments/exp03_week3_tournament.py --game kuhn_poker --cfr-iters 10000 --n-pairs 10000 --seeds 0 1 2 3 4
```

Outputs:

- `results/tables/week03_cfr_convergence.csv`
- `results/figures/week03_cfr_convergence.png`
- `results/tables/week03_payoff_matrix.csv`
- `results/tables/week03_pairwise_with_ci.csv`
- `results/figures/week03_payoff_matrix.png`

For a fast smoke run, use `--iters 500 --cfr-iters 500 --n-pairs 1000`.
