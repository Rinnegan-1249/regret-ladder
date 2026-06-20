# CLAUDE.md — Regret Ladder

Summer research project on poker AI / regret minimization, built on OpenSpiel.
Weekly deliverables for a professor: clean experiments, math explanations, plots, tables.

## Standing instructions for Claude

1. **Keep this file updated.** Whenever meaningful work is done (new week's experiments,
   algorithm changes, refactors), update the "Progress log" and any stale sections here.
2. **Push to GitHub after updates.** When a work session produces committed changes,
   push to `origin main` (https://github.com/Rinnegan-1249/regret-ladder.git). Use clear,
   logically separated commits.
3. **Maintain `REMINDERS.md`.** Whenever something needs the user's manual attention
   (a writeup to update, a figure to eyeball, a decision to make, stale files), add a
   checklist item there instead of just mentioning it in chat.
4. **Never change the scientific behavior of implemented algorithms** (regret matching,
   CFR) without explicit agreement. Plotting/IO fixes are fine; update rules, payoffs,
   and seeding schemes are not.
5. Outputs are deliverables: CSVs → `results/tables/`, plots → `results/figures/`
   (both committed). Logs go to `results/logs/` (gitignored). Don't overwrite committed
   deliverables with smoke-run output — use a temp dir or small-run output paths.

## Project roadmap (ladder)

Week 1: baselines on Kuhn Poker → Week 2: regret matching on RPS → Week 3: Vanilla CFR
on Kuhn → Week 4+: CFR+, MCCFR (outcome/external sampling), Leduc Poker, Hold'em
terminology / simplified Hold'em / abstraction. Full Texas Hold'em is out of scope.

## Current status: Weeks 1–6 experiment scripts done; full runs complete

- **Weeks 5–6 (Leduc Poker):** All four solvers ported to Leduc Poker (9,457 tree nodes,
  936 infosets — 78×/394× larger than Kuhn). `exp05_leduc_cfr_variants.py`: CFR vs CFR+
  convergence + compressibility on Leduc (3 figures + CSV); `exp06_leduc_mccfr.py`:
  4-way overlay (nodes/iter/time) on Leduc; `exp06_leduc_tournament.py`: 7-agent round-
  robin (5 baselines + CFR + CFRPlus) with duplicate-pair evaluation. Validation scripts:
  `validate_week5.py` (CFR/CFR+ vs OpenSpiel) and `validate_week6.py` (OS/ES vs OpenSpiel).
  Smoke-tested: all scripts pass, 41/41 tests green. Full runs done and committed
  (commits `1225760`, `b328b83`, `82fc984`): exp05 at 10,000 iters
  (`week05_leduc_cfr_variants.csv`); exp06 4-way overlay at CFR/CFR+ 5,000 iters,
  OS-MCCFR 500,000 iters, ES-MCCFR 100,000 iters (`week06_leduc_mccfr.csv`);
  exp06 tournament at 5,000 pairs × 5 seeds, CFR/CFR+ trained 5,000 iters
  (`week06_leduc_payoff_matrix.csv` — CFR/CFR+ both dominate baselines ~0.55
  chips/hand, head-to-head CFR vs CFR+ ≈ 0.0006 chips/hand). No algorithm code
  changed — solvers are game-agnostic.

- **Week 4:** `CFRPlus` (`agents/cfr_plus.py`, Tammelin 2014: regret-matching+ floor,
  alternating updates, linear weighted averaging w_t = max(t-d, 0)). exp04: CFR+ avg
  exploitability 9.1e-06 vs CFR 2.3e-03 at 10k iters; CFR+ current strategy converges,
  CFR current oscillates; exact Kuhn Nash family recovered (alpha=0.2226, bet K = 3*alpha).
  Also `OutcomeSamplingMCCFR` (`agents/mccfr_outcome.py`, eps-greedy 0.6, importance-
  corrected Eq.10 updates) and `ExternalSamplingMCCFR` (`agents/mccfr_external.py`, Eq.11,
  simple averaging at opponent nodes) per Lanctot et al. 2009; both have `nodes_touched`
  counters and seeded rngs. exp04b: 4-way overlay (CFR, CFR+, OS, ES) by nodes touched /
  iterations / wall-clock. All validated vs OpenSpiel reference solvers
  (validate_week3/4/4b scripts).

- **Week 1:** 5 baseline agents (random, always_call, always_fold, rule_based,
  ev_heuristic), duplicate-pair evaluation, multi-seed round-robin tournament on Kuhn.
- **Week 2:** `RegretMatchingAgent` on RPS. The experiment uses **expected-utility
  updates** (`update_expected`): utilities computed against the opponent's full strategy
  distribution, baseline = own expected utility; small seeded random initial regrets
  break the uniform fixed point. The sampled-action `update()` also still exists.
  Average strategy converges to Nash (1/3, 1/3, 1/3); regret decays ~O(1/T) on log-log.
- **Week 3:** from-scratch tabular `VanillaCFR` (simultaneous updates with frozen regret
  tables) on Kuhn, exploitability tracked per iteration, validated against OpenSpiel's
  `CFRSolver`; 7-agent payoff cross-table (5 baselines + our CFR + OpenSpiel CFR).

## Layout (see docs/repo_structure.md for detail)

- `poker_ai/` — installed package (`pip install -e .`), all reusable code:
  `agents/` (baselines, `regret_matching.py`, `cfr.py`, `cfr_plus.py`, `openspiel_solver.py`),
  `env/rps.py`, `evaluation/` (`tournament.py`, `exploitability.py`, `stats.py`),
  `utils/seeding.py`.
- `experiments/` — weekly deliverables (exp01=W1, exp02=W2, exp03=W3, exp04/04b=W4,
  exp05=W5, exp06×2=W6). Run from repo root.
- `scripts/` — demos, human-play, report generators, `validate_week3/4/4b/5/6.py`.
- `tests/` — pytest sanity tests (41 passing as of 2026-06-20; `test_leduc_smoke.py` covers
  all 4 solvers on Leduc).
- `docs/` — roadmap PDF, `repo_audit_before_cleanup.md`, `repo_structure.md`.
- `archive/legacy_before_cleanup/` — superseded files, never delete things, archive them.

## Commands

```cmd
.venv\Scripts\python.exe -m pytest -q
python experiments\exp01_baseline_tournament.py --game kuhn_poker --n-pairs 10000 --seeds 0 1 2 3 4
python experiments\exp02_rps_convergence.py --seed 0 --iterations 100000   (repeat seeds 0-4)
python experiments\exp03_train_cfr.py --game kuhn_poker --iters 10000
python experiments\exp03_week3_tournament.py --game kuhn_poker --cfr-iters 10000 --n-pairs 10000 --seeds 0 1 2 3 4
python scripts\validate_week3.py --game kuhn_poker --iters 1000
python experiments\exp04_cfr_variants_kuhn.py --game kuhn_poker --iters 10000 --delay 0
python scripts\validate_week4.py --game kuhn_poker --iters 1000
python experiments\exp04b_mccfr_kuhn.py --iters 10000 --os-iters 200000 --es-iters 50000 --seeds 0 1 2
python scripts\validate_week4b.py --os-iters 100000 --es-iters 20000
python experiments\exp05_leduc_cfr_variants.py --iters 10000
python scripts\validate_week5.py --iters 10000
python experiments\exp06_leduc_mccfr.py --iters 5000 --os-iters 500000 --es-iters 100000 --seeds 0 1 2
python experiments\exp06_leduc_tournament.py --cfr-iters 5000 --n-pairs 5000 --seeds 0 1 2 3 4
python scripts\validate_week6.py --os-iters 100000 --es-iters 20000
```

All experiment scripts accept output-path overrides (`--out` / `--outdir` / `--out-dir`)
— use them for smoke runs.

## Gotchas

- Week 1 vs Week 3 agent interfaces differ (`act(state)` vs `act(state, rng)`);
  `tournament.call_agent_act` dispatches by signature inspection. Keep both working.
- `run_round_robin` returns `(matrix_df, long_df)` and takes a loaded pyspiel game +
  a list of agents (names from `agent.name`). The old `round_robin(game_name=..., dict)`
  API is gone — exp01 was updated for this on 2026-06-12.
- The committed `exp01_baseline_tournament.csv` still has the pre-refactor column schema;
  the Week 1 report generators may break on a regenerated CSV (see REMINDERS.md).
- Expected-utility RPS from exactly-uniform start is a fixed point — do not remove the
  seeded random regret initialization in exp02.

## Web demo (`web/`)

FastAPI app (`uvicorn web.app:app`): RPS + Kuhn play vs real bots, live SSE training
graphs, theory/results/references pages. Key modules: `web/bots.py` (policy training +
JSON cache in gitignored `web/cache/`), `web/rps_engine.py` & `web/kuhn_engine.py`
(in-memory match stores), `web/training_stream.py` (SSE generators with hard iteration
caps), templates+vanilla JS with Plotly/KaTeX CDN. Tests in `tests/test_web.py` use a
`fast_cfr_bots` fixture (tiny budgets, tmp cache). Gotchas: (1) PowerShell mangles
double quotes in inline `python -c` here-strings — use single quotes/percent-
formatting. (2) `Plotly.react` compares trace arrays BY REFERENCE — arrays mutated in
place with push() are treated as unchanged and never redraw; always pass `.slice()`
copies. (3) To debug client-side chart issues empirically: headless Chrome screenshot
of `web/static/debug_charts.html` (auto-runs both training streams through the real JS)
via `chrome --headless=new --screenshot=... --virtual-time-budget=25000 <url>`, then
Read the PNG.

## Progress log

- **2026-06-21 (later)** — Wrote `reports/Final_Report.md`: consolidated Week 1–6
  write-up (Week 7 deliverable) covering every implemented agent/solver, all key
  numeric results pulled directly from `results/tables/*.csv` (baseline tournament,
  RPS regret-matching convergence, Vanilla CFR vs OpenSpiel, CFR+/MCCFR on Kuhn,
  CFR/CFR+/MCCFR scaling to Leduc, head-to-head significance tests, and the
  validate_week5/6 ratios from the prior session). Draft — flagged in REMINDERS.md
  for review; a presentation/deck still needs to be prepared separately.

- **2026-06-21** — Ran `validate_week5.py` (10k iters) and `validate_week6.py`
  (100k OS / 20k ES), neither of which had actually been executed before despite
  being marked complete. Both pass: CFR+ tracks OpenSpiel within 0.75–1.0× throughout;
  vanilla CFR drifts to 5.11× by iter 10000 (still same order of magnitude — expected
  from simultaneous vs. alternating updates). OS/ES-MCCFR track OpenSpiel almost
  exactly at every checkpoint. Logs in `results/logs/` (gitignored). Weeks 5–6 are now
  fully done: scripts, full runs, and validation all complete.

- **2026-06-20** — Weeks 5–6 experiment scripts implemented (Leduc Poker scaling).
  Leduc has 9,457 tree nodes and 936 infosets (394× / 78× larger than Kuhn); no solver
  code changes needed — all four are game-agnostic. New files: `exp05_leduc_cfr_variants.py`
  (CFR vs CFR+, 3 figs + CSV), `exp06_leduc_mccfr.py` (4-way overlay, 3 figs + CSV),
  `exp06_leduc_tournament.py` (7-agent Leduc cross-table), `validate_week5.py`,
  `validate_week6.py`, `tests/test_leduc_smoke.py` (4 new tests; 41 total, all green).
  Smoke runs all passed. Full runs pending — CFR on Leduc ≈ 0.145 s/iter (10k iters ≈ 24 min).

- **2026-06-13 (later)** — Site restructured into sections: nav = Home / Games /
  Foundations / Regret / Results / References. New pages: /games (game index),
  /foundations (extensive-form model), /regret (regret → CFR literature ladder).
  Home is now a directory. Also: static cache-busting (?v=mtime), Plotly.react
  .slice() fix for the blank live charts.
- **2026-06-13** — Website redesign: dark neon theme (mint accent, Space Grotesk/Inter/
  JetBrains Mono, numbered sections, glass cards), gamified play (RPS duel reveal
  animation + streak + adaptive strategy bars; Kuhn poker-table with CSS 3D card flip
  at showdown, pot/betting chips, bankroll sparkline). Fixed missing live charts:
  Plotly in hidden tab panes had zero width — initTabs now resizes on pane activation
  and training tabs draw placeholder axes immediately (shared darkLayout helper in
  training.js).
- **2026-06-12 (evening)** — Built the interactive website (`web/`): intro/home with
  Zinkevich common theory, RPS page (human/distribution/frozen-RM/adaptive-RM seats,
  hidden simultaneous reveal, live RM training stream, observability theory note with
  Hart & Mas-Colell + Blackwell citations), Kuhn page (rules + betting-tree SVG, 5
  baseline + 4 CFR-family bots, human play with hidden cards, live training for all 4
  solvers with per-infoset strategy traces + exploitability), results page from real
  figures, references page serving the 3 PDFs. 19 new tests (34 total).
- **2026-06-12 (later still)** — Week 4 part 2: implemented OS-MCCFR and ES-MCCFR per
  Lanctot et al. 2009 (paper filed as `Research_Papers/MCCFR_Lanctot2009.pdf`);
  `experiments/exp04b_mccfr_kuhn.py` 4-way comparison (CFR, CFR+, OS, ES) with paper-style
  nodes-touched plot; `scripts/validate_week4b.py` vs OpenSpiel solvers; 4 new tests
  (15 total). Roadmap Week 4 complete; ES-MCCFR done early from Week 5.
- **2026-06-12 (later)** — Week 4 part 1: implemented CFR+ (`agents/cfr_plus.py`) per
  Tammelin 2014 (paper filed as `Research_Papers/CFRplus_Tammelin2014.pdf`);
  `experiments/exp04_cfr_variants_kuhn.py` (4 figures + CSV: exploitability of avg+current
  strategies vs iterations and vs wall-clock, zero-regret compressibility, current-strategy
  Nash-family trace); `scripts/validate_week4.py` vs OpenSpiel CFRPlusSolver; 3 new tests
  (11 total). OS-MCCFR remains for Week 4 completion.
- **2026-06-12** — Repo audit + cleanup (docs, .gitignore dedupe, archived week3
  README/requirements, README overhaul, 3 new tests). Switched exp02 RPS to
  expected-utility regret updates and regenerated all Week 2 results (seeds 0–4).
  Fixed exp01 + a stale test broken by the Week 3 tournament refactor. Committed Week 3
  work and pushed everything (commits `b0e5cad`, `87baf8b`).
