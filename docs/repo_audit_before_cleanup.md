# Repository Audit — Before Cleanup (2026-06-12)

Snapshot taken before the cleanup + RPS expected-utility change. Working tree at this point
had uncommitted Week 3 work (see "Git state" below).

## Baseline test run

`python -m pytest -q` → **1 failed, 2 passed**

- `tests/test_duplicate_pairing.py` — FAILED: calls `duplicate_match(..., base_seed=0)`, but the
  Week 3 refactor of `poker_ai/evaluation/tournament.py` renamed the parameter to `seed`.
  Stale test, not a logic bug. Fixed during cleanup.
- `tests/test_agents_choose_legal_actions.py` — passed.
- `tests/test_regret_matching_rps.py` — passed.

## Directory tree (excluding .venv, .git, __pycache__)

```
Regret Ladder/
├── README.md / README_week3.md / pyproject.toml
├── requirements.txt / requirements_week3.txt / .gitignore
├── poker_ai_research_roadmap.md.pdf        (loose at root)
├── poker_ai/                               [installed package, pip install -e .]
│   ├── agents/    base, random_agent, always_call, always_fold, rule_based,
│   │              ev_heuristic, baselines, cfr, regret_matching, openspiel_solver
│   ├── env/       rps.py
│   ├── evaluation/ tournament.py, exploitability.py, stats.py
│   └── utils/     seeding.py
├── experiments/   exp01_baseline_tournament, exp02_rps_convergence,
│                  exp03_train_cfr, exp03_week3_tournament
├── scripts/       smoke_test_openspiel, observe_openspiel_game,
│                  demo_bot_duplicate_pairs, play_human_round_robin,
│                  play_human_mystery_bots, make_week01_report,
│                  make_week01_brief_report, validate_week3
├── tests/         test_agents_choose_legal_actions, test_duplicate_pairing,
│                  test_regret_matching_rps
├── results/       tables/ (exp01, exp02 seed0-4, week03 csv), figures/ (week02, week03 png),
│                  logs/ (gitignored), checkpoints/ (empty)
├── reports/weekly/  week01.md, Detailed_Report.pdf
├── slides/weekly/   Week1_ppt.pdf
├── notebooks/, configs/  (empty placeholders, .gitkeep)
└── Research_Papers/ NIPS07-cfr.pdf
```

## Classification

**Final source code (the package):** everything under `poker_ai/`. All experiments/scripts/tests
import it via `from poker_ai...` (no sys.path hacks; relies on the editable install).

**Experiments (weekly deliverables):** `experiments/exp01_*` (Week 1), `exp02_*` (Week 2),
`exp03_*` (Week 3).

**Utility / interactive scripts:** everything in `scripts/` (demos, human play, report
generators, OpenSpiel smoke test, Week 3 validation against OpenSpiel's CFRSolver).

**Outputs / results:** `results/tables/*.csv`, `results/figures/*.png`, `reports/`, `slides/`.
Already organized by type — nothing scattered.

## Suspected duplicates

**None found.** No `_old` / `_v2` / copy files. Minor near-duplicates noted but kept:

- `scripts/make_week01_report.py` vs `scripts/make_week01_brief_report.py` — two report
  formats, both intentional.
- `poker_ai/agents/baselines.py` — import aggregator; **used** by
  `experiments/exp03_week3_tournament.py`, so kept.

## Real issues found

1. **Bug:** `experiments/exp02_rps_convergence.py` lines 163–174 — an orphaned leftover block
   inside `plot_average_regret()` that re-styles and re-saves the figure with the wrong title
   ("Per-Action Regret Decay") after `plt.close()`. This is why
   `results/figures/week02_rps_average_regret_seed0.png` showed as modified in git.
2. **Stale test:** `tests/test_duplicate_pairing.py` uses the old `base_seed` kwarg (see above).
3. **Redundant files at root:** `README_week3.md` (quick-start now merged into `README.md`)
   and `requirements_week3.txt` (subset of `requirements.txt`) → archived to
   `archive/legacy_before_cleanup/`.
4. **Loose root file:** `poker_ai_research_roadmap.md.pdf` → moved to `docs/`.
5. **.gitignore:** duplicated entries (`.venv/`, `__pycache__/`, `*.pyc` listed twice) → deduped.

## Files archived (nothing deleted)

- `archive/legacy_before_cleanup/README_week3.md`
- `archive/legacy_before_cleanup/requirements_week3.txt`

## Git state at audit time

Uncommitted modifications: `experiments/exp02_rps_convergence.py`, `poker_ai/env/rps.py`,
`poker_ai/evaluation/tournament.py` (+221 lines, Week 3 refactor),
`results/figures/week02_rps_average_regret_seed0.png`. Untracked: all Week 3 files
(`poker_ai/agents/cfr.py`, `openspiel_solver.py`, `baselines.py`,
`poker_ai/evaluation/exploitability.py`, `experiments/exp03_*`, `scripts/validate_week3.py`,
week03 results, `Research_Papers/`, `README_week3.md`, `requirements_week3.txt`).
