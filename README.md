# PokerAI Summer Project — Week 1 Starter Repo

This repository is the Week 1 scaffold for a research-grade poker bot project.

Week 1 goal:

1. Install OpenSpiel and verify `kuhn_poker` + `leduc_poker` load.
2. Implement simple baseline agents.
3. Run a duplicate-pair tournament on Kuhn Poker.
4. Save a results CSV that can be shown to your professor.

## Windows quickstart

Open **PowerShell** in the folder where you want the repo.

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
python scripts\smoke_test_openspiel.py
pytest -q
python experiments\exp01_baseline_tournament.py --game kuhn_poker --n-pairs 10000 --seeds 0 1 2 3 4
```

If PowerShell blocks venv activation:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

## Expected smoke-test output

You should see something like:

```text
OpenSpiel imported successfully.
Loaded kuhn_poker: players=2, actions=2
Loaded leduc_poker: players=2, actions=3
```

## Repo structure

```text
poker_ai/
  agents/          baseline agents
  evaluation/      duplicate tournament + statistics
  utils/           seeding helpers
experiments/       runnable experiment scripts
scripts/           smoke tests and utilities
results/           generated logs/tables/figures
```

## What to show in Week 1 meeting

- Screenshot of smoke test showing Kuhn + Leduc load.
- Pairwise baseline tournament table from `results/tables/exp01_baseline_tournament.csv`.
- 1 slide explaining why payoff/chips per hand is better than win rate.
- 1 slide explaining why OpenSpiel is the right environment for CFR/MCCFR later.
