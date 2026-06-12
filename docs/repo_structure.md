# Repository Structure (after 2026-06-12 cleanup)

The repo follows a package + experiments + outputs split. All commands are run from the
repo root with the venv active; the `poker_ai` package is installed editable
(`pip install -e .`), so no sys.path hacks are needed anywhere.

```
regret-ladder/
├── poker_ai/                  # THE library: all algorithm/source code lives here
│   ├── agents/                #   baselines, RegretMatchingAgent, VanillaCFR, PolicyAgent
│   ├── env/                   #   toy game definitions (rps.py)
│   ├── evaluation/            #   tournament, exploitability, stats
│   └── utils/                 #   seeding
├── experiments/               # weekly deliverable scripts (exp01=W1, exp02=W2, exp03=W3)
├── scripts/                   # utilities: demos, human play, report generators, validation
├── tests/                     # pytest sanity tests (run: python -m pytest -q)
├── results/
│   ├── tables/                # committed CSV deliverables
│   ├── figures/               # committed PNG deliverables
│   ├── logs/                  # regenerated, gitignored
│   └── checkpoints/           # gitignored
├── reports/weekly/            # weekly markdown/PDF reports
├── slides/weekly/             # presentation decks
├── docs/                      # roadmap PDF, repo_audit_before_cleanup.md, this file
├── Research_Papers/           # reference papers (NIPS07 CFR)
├── notebooks/, configs/       # placeholders for later weeks
└── archive/legacy_before_cleanup/  # superseded files, kept (nothing deleted)
```

## Conventions

- **Source code vs experiments:** anything reusable goes in `poker_ai/`; an experiment
  script in `experiments/` should only wire together package functions, parse CLI args,
  and write outputs to `results/`.
- **experiments/ vs scripts/:** `experiments/` holds the reproducible weekly deliverables
  the professor sees; `scripts/` holds interactive demos, smoke tests, and report
  generators.
- **Outputs:** CSVs → `results/tables/`, plots → `results/figures/` (both committed);
  logs → `results/logs/` (gitignored, regenerated on each run).
- **Naming:** experiment files are `expNN_<topic>.py`; output files are prefixed
  `expNN_` or `weekNN_`.

## Archived files

`archive/legacy_before_cleanup/` holds files superseded during cleanup (nothing was
deleted):

- `README_week3.md` — Week 3 quick-start, merged into the main `README.md` (section 12).
- `requirements_week3.txt` — subset of `requirements.txt`.

## Notable changes made during cleanup (2026-06-12)

- `experiments/exp02_rps_convergence.py` switched from sampled-action regret updates to
  **expected-utility updates** (`RegretMatchingAgent.update_expected`): regrets are
  computed against the opponent's full strategy distribution. A small seeded random
  regret initialization breaks the uniform fixed point. All Week 2 CSVs/figures were
  regenerated.
- Removed an orphaned plotting block in `exp02` that overwrote the regret figure with a
  wrong title.
- `tests/test_duplicate_pairing.py` updated to the Week 3 `duplicate_match(seed=...)`
  signature.
- Added tests: `test_regret_matching_properties.py`, `test_cfr_smoke.py`,
  `test_evaluation_keys.py`.
- Deduplicated `.gitignore`; moved the roadmap PDF into `docs/`.

See `docs/repo_audit_before_cleanup.md` for the pre-cleanup state.
