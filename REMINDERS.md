# Reminders — things to review manually

## From the 2026-06-21 session (Week 7: Final Report)

- [ ] **Review `reports/Final_Report.md`** — generated draft covering Weeks 1–6 with
  all key numeric results (baseline tournament, RPS convergence, Vanilla CFR vs
  OpenSpiel, CFR+/MCCFR on Kuhn, CFR/CFR+/MCCFR on Leduc, validation ratios). Check it
  reads well for the professor and that no numbers look off before treating it as final.
- [ ] **Decide on a presentation/slide deck** to accompany the final report — the
  roadmap's Week 7 also calls for "prepare final report and presentation"; only the
  written report has been generated so far.

## From the 2026-06-20 session (Weeks 5–6: Leduc Poker)

- [x] **Run exp05 full run** — DONE. Results in `results/figures/week05_*.png` and
  `results/tables/week05_leduc_cfr_variants.csv`. Headline: CFR+ 2164× better than CFR
  at 10k iters (4.823e-06 vs 1.044e-02). CFR current strategy oscillates (1.101); CFR+
  current converges (2.058e-03). Speed-up grows with game size (Kuhn was 255×).

- [x] **Run validate_week5** — DONE (10k iters). CFR+ ratio 0.75–1.0× vs OpenSpiel
  throughout. Vanilla CFR ratio grows from 1.04× (iter 10) to 5.11× (iter 10000,
  0.01044 vs 0.00204) — same order of magnitude, consistent with the known
  simultaneous-vs-alternating-update difference (CFR current strategy oscillates,
  CFR+ converges). Log: `results/logs/validate_week5_run.txt`.

- [x] **Run exp06 MCCFR full run** — DONE. `week06_exploitability_vs_nodes.png` is the
  headline. On Leduc, full-traversal solvers dominate: CFR+ at 94.6M nodes = 1.486e-05;
  OS-MCCFR at 7.88M nodes = 2.337e-01; ES-MCCFR at 4.49M nodes = 6.686e-02. MCCFR
  needs much larger iteration budgets on Leduc due to high sample variance.

- [x] **Run exp06 tournament full run** — DONE. CFR5000 and CFRPlus5000 both dominate all
  5 baselines (~0.55 chips/hand). Head-to-head difference is 0.0006 chips/hand (near-Nash
  equivalence at 5k iters). See `week06_leduc_payoff_matrix.png`.

- [x] **Run validate_week6** — DONE (100k OS / 20k ES). Both solvers track OpenSpiel
  closely at every checkpoint (final exploitability: OS-MCCFR 0.5038 vs 0.5002,
  ES-MCCFR 0.1778 vs 0.1826). Log: `results/logs/validate_week6_run.txt`.

- [ ] **Write-up note for the Leduc deck**: Two key scaling results: (1) CFR+ speed-up
  grows from 255× on Kuhn to 2164× on Leduc at 10k iters — the regret-floor interacts
  with more infosets to produce dramatically faster convergence. (2) On Leduc, full-
  traversal solvers (especially CFR+) are more efficient per node than MCCFR samplers
  because sample variance grows with game tree size.

- [ ] **Eyeball the 7 new figures** in `results/figures/week05_*.png` and
  `results/figures/week06_*.png` before presenting to professor.



Items Claude flags for human review land here. Check them off (or delete them) once handled.

## From the 2026-06-13 session (website redesign)

- [ ] **Visually verify the redesign** (hard-refresh with Ctrl+F5 to bust cached
  CSS/JS): dark theme everywhere, RPS duel animation + verdict glow, Kuhn card flip at
  showdown (and face-down on folds), and — the bug you reported — BOTH charts now
  render in each Live-training tab, including after switching tabs mid-training.
- [ ] If any chart still looks blank, open the browser console (F12) and send me the
  error — chart errors now also print into the status line under the Train button.

## From the 2026-06-12 session (website)

- [ ] **Proofread the site's theory text** (`web/templates/index.html`, `rps.html`
  theory tab, `kuhn.html` theory tab) — the math follows Zinkevich/Tammelin/Lanctot and
  the observability note cites Hart & Mas-Colell 2000/2001 + Blackwell 1956; verify the
  wording matches how you'd present it to your professor.
- [ ] **Try the site end-to-end yourself**: `uvicorn web.app:app` → play the adaptive
  RPS bot (spam rock, watch it shift to paper), play Kuhn vs CFR+, run a live training
  for each algorithm. First CFR-bot use trains policies (~45s total, then cached).
- [ ] **Consider screenshots** of the live-training graphs and play UI for the Week 4
  deck / final report.
- [ ] **Deployment decision (later)**: the site needs Python, so GitHub Pages won't
  host it; if you want it public, a free Render/Railway tier or a recorded demo video
  are the usual options.

## From the 2026-06-12 session (Week 4 part 2: MCCFR)

- [ ] **Review the three week04b figures** (`results/figures/week04b_*.png`) — the
  nodes-touched overlay is the paper-style headline for the Week 4 deck's "three-curve
  plot" requirement (we have four curves: CFR, CFR+, OS, ES).
- [ ] **Deck takeaway to write up:** the variance-vs-computation trade-off — OS touches
  ~10 nodes/iteration but needs many more iterations (1/delta factor in Theorem 5);
  ES is the sweet spot on Kuhn (Theorem 4: constant-factor more iterations at sqrt
  per-iteration cost); CFR+ still wins per full traversal. Note OS/ES used 3 seeds.
- [ ] **Week 5 next:** Leduc Poker experiments — all four solvers already accept any
  two-player pyspiel game, so exp05 is mostly a budget/runtime question.
- [ ] **Optional:** epsilon sweep for OS-MCCFR (paper found 0.6 best across games;
  could verify on Kuhn for the writeup).

## From the 2026-06-12 session (Week 4: CFR+)

- [ ] **Review the four week04 figures** in `results/figures/` (exploitability vs
  iterations / vs time, zero-regret fraction, current-strategy trace) — these are the
  candidates for the roadmap's 7-slide Week 4 deck.
- [ ] **Prepare the Week 4 deck** (roadmap deliverable): CFR+ update rule
  (regret-matching+ formula), linear averaging math, the headline 4-curve plot, and the
  takeaway table (CFR+ avg 9.1e-06 vs CFR 2.3e-03 at 10k iters; current strategy
  converges for CFR+, oscillates for CFR; recovered Nash family alpha = 0.2226 with
  P(bet|K) = 3*alpha exactly).
- [ ] **OS-MCCFR is still pending** — the roadmap's Week 4 pairs CFR+ with
  outcome-sampling MCCFR. exp04 is built so a third curve can be added.
- [ ] **Optional:** decide whether to run a delay sweep (`--delay 100/500`) to reproduce
  the paper's Figure-2-style "averaging delay" effect for the writeup. On Kuhn the effect
  is likely small; on Leduc (Week 5) it may be more visible.

## From the 2026-06-12 session (cleanup + RPS expected-utility change)

- [ ] **Update the Week 2 report/slides math writeup.** The RPS experiment now uses
  expected-utility regret updates (`RegretMatchingAgent.update_expected`): regrets are
  computed against the opponent's full strategy distribution, with the baseline being the
  player's own expected utility. It also uses small seeded random initial regrets to break
  the uniform fixed point (uniform-vs-uniform has zero expected regret everywhere, so
  nothing would ever move). The writeup your professor sees should describe this rule,
  not the old sampled-action rule.
- [ ] **Eyeball the regenerated Week 2 figures** in `results/figures/week02_*.png`
  (seeds 0–4). Convergence is now much smoother/deterministic; make sure they tell the
  story you want for the deliverable.
- [ ] **Week 1 CSV schema changed — committed exp01 results are stale.** The Week 3
  `tournament.py` refactor changed `run_round_robin`'s output columns
  (`agent_a, agent_b, mean, ci_low, ci_high, p_value, n, seeds`). The committed
  `results/tables/exp01_baseline_tournament.csv` still has the old schema
  (`mean_payoff_to_a`, `win_rate_a`, ...). If you rerun exp01, the new CSV will look
  different, and `scripts/make_week01_report.py` / `make_week01_brief_report.py` likely
  still expect the old columns — test them before regenerating the Week 1 report.
  README section 10 (Metrics) also still documents the old column names.
- [ ] **Decide whether to show sampled vs expected updates in Week 2.** The old
  sampled-action `update()` still exists in `RegretMatchingAgent`. Comparing both update
  rules (noisy O(1/√T) vs smooth decay) could make a nice plot/discussion point.
- [ ] **Confirm the archive is OK.** `archive/legacy_before_cleanup/` holds the old
  `README_week3.md` and `requirements_week3.txt` (content merged into the main
  README/requirements). Delete the folder later if you're happy.
- [ ] **Cosmetic:** `pyproject.toml` package name is `poker-ai` while the GitHub repo is
  `regret-ladder`. Harmless, but rename if you want consistency.
