# Reminders — things to review manually

Items Claude flags for human review land here. Check them off (or delete them) once handled.

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
