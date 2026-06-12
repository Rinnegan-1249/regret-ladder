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

## Current status: Weeks 1–3 done; Week 4 CFR+ done (OS-MCCFR pending)

- **Week 4 (partial):** `CFRPlus` in `poker_ai/agents/cfr_plus.py` (Tammelin 2014:
  regret-matching+ floor, alternating updates, linear weighted averaging with delay d).
  Validated vs OpenSpiel `CFRPlusSolver`. exp04 results: CFR+ avg-strategy exploitability
  9.1e-06 vs CFR 2.3e-03 at 10k iters; CFR+ current strategy converges (8.5e-03, decaying)
  while CFR current oscillates (~1.5e-01); recovered exact Kuhn Nash family member
  (alpha=0.2226, bet K = 3*alpha). OS-MCCFR still needed to complete roadmap Week 4.

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
- `experiments/` — weekly deliverables (exp01=W1, exp02=W2, exp03=W3). Run from repo root.
- `scripts/` — demos, human-play, report generators, `validate_week3.py`.
- `tests/` — pytest sanity tests (8 passing as of 2026-06-12).
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

## Progress log

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
