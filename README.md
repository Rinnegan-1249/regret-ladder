# Regret Ladder — Poker AI Research Project

This project is built around OpenSpiel, beginning with simple baseline agents on Kuhn Poker and progressing toward regret-minimization methods such as Regret Matching, Vanilla CFR, CFR+, and Monte Carlo CFR.

**Current status: Weeks 1–3 implemented** — baseline tournament on Kuhn Poker (Week 1), expected-utility regret matching on Rock-Paper-Scissors (Week 2), and from-scratch Vanilla CFR on Kuhn Poker validated against OpenSpiel, with exploitability tracking (Week 3).

The central goal is not to jump directly to full Texas Hold'em. The project is intentionally narrow and deep: build a clean, reproducible pipeline on small imperfect-information poker games, validate each step, and only then scale from Kuhn Poker to Leduc Poker.

---

## 1. Project Objective

This project studies poker as an imperfect-information game and builds a ladder of increasingly stronger agents:

1. Random and degenerate fixed-policy agents.
2. Domain-knowledge and expected-value heuristic agents.
3. Regret Matching on a normal-form toy game.
4. Vanilla CFR on Kuhn Poker.
5. CFR+ and Monte Carlo CFR variants.
6. Tabular CFR/MCCFR on Leduc Poker.
7. Optional stretch: NFSP / Deep CFR on Leduc.

The final deliverable is a reproducible GitHub repository, experiment results, weekly reports, and a final presentation/write-up explaining both the implementation and the game-theoretic ideas.

---

## 2. Why Poker?

Poker is a natural testbed for imperfect-information decision-making:

- players do not observe the opponent's private cards,
- actions reveal partial information,
- strategies must sometimes randomize,
- simple win rate is not enough because payoff sizes matter,
- equilibrium concepts such as Nash equilibrium and exploitability are meaningful.

This makes poker a good environment for understanding why regret minimization methods such as CFR are useful.

---

## 3. Framework Choice

The primary framework is **OpenSpiel**.

OpenSpiel provides:

- built-in games such as `kuhn_poker` and `leduc_poker`,
- legal action generation,
- chance nodes and card-dealing probabilities,
- state transitions,
- terminal payoff calculation,
- reference implementations of CFR-style algorithms,
- exploitability / best-response tooling for later stages.

In this repository, OpenSpiel acts as the game engine/referee. Our code supplies the agents, tournament loop, duplicate-pair evaluation, metrics, reports, and experiments.

---

## 4. Games

### Kuhn Poker

Week 1 starts with `kuhn_poker`.

Kuhn Poker has:

- three cards: Jack, Queen, King,
- two players,
- one private card per player,
- one betting round,
- simple action space,
- small enough game tree to inspect and debug manually.

OpenSpiel card encoding for Kuhn Poker:

| Card ID | Card |
|---:|---|
| `0` | Jack |
| `1` | Queen |
| `2` | King |

OpenSpiel action encoding:

| Action ID | OpenSpiel symbol | Meaning |
|---:|---|---|
| `0` | `p` | pass/check if no bet is pending; fold/pass if facing a bet |
| `1` | `b` | bet if no bet is pending; call if facing a bet |

### Leduc Poker

Leduc Poker is the next scaling target. It introduces a public board card and multiple betting rounds, while still remaining tractable for tabular CFR/MCCFR experiments.

Full Texas Hold'em is explicitly out of scope for the core project because it requires card abstraction, action abstraction, subgame solving, and much more compute.

---

## 5. Repository Structure

```text
regret-ladder/
├── README.md
├── pyproject.toml
├── requirements.txt
├── poker_ai/                      # installed package (pip install -e .)
│   ├── agents/
│   │   ├── base.py                # abstract Agent interface
│   │   ├── random_agent.py        # Week 1 baselines...
│   │   ├── always_call.py
│   │   ├── always_fold.py
│   │   ├── rule_based.py
│   │   ├── ev_heuristic.py
│   │   ├── baselines.py           # convenience aggregator for the baselines
│   │   ├── regret_matching.py     # Week 2: regret matching (sampled + expected updates)
│   │   ├── cfr.py                 # Week 3: VanillaCFR + PolicyAgent
│   │   └── openspiel_solver.py    # Week 3: OpenSpiel CFRSolver wrapper
│   ├── env/
│   │   └── rps.py                 # Rock-Paper-Scissors payoff matrix and helpers
│   ├── evaluation/
│   │   ├── tournament.py          # duplicate-pair matches, round-robin, paper-style tables
│   │   ├── exploitability.py      # OpenSpiel exploitability wrapper
│   │   └── stats.py               # MatchStats, confidence intervals
│   └── utils/
│       └── seeding.py
├── experiments/                   # weekly deliverable experiments
│   ├── exp01_baseline_tournament.py   # Week 1
│   ├── exp02_rps_convergence.py       # Week 2
│   ├── exp03_train_cfr.py             # Week 3: CFR convergence + exploitability
│   └── exp03_week3_tournament.py      # Week 3: cross-table with CFR agents
├── scripts/                       # utilities, demos, report generators
│   ├── smoke_test_openspiel.py
│   ├── observe_openspiel_game.py
│   ├── demo_bot_duplicate_pairs.py
│   ├── play_human_round_robin.py
│   ├── play_human_mystery_bots.py
│   ├── make_week01_report.py
│   ├── make_week01_brief_report.py
│   └── validate_week3.py          # validate VanillaCFR vs OpenSpiel CFRSolver
├── tests/                         # pytest sanity tests
├── results/
│   ├── tables/                    # CSV result tables (tracked)
│   ├── figures/                   # PNG plots (tracked)
│   ├── logs/                      # generated logs (gitignored)
│   └── checkpoints/               # (gitignored)
├── reports/weekly/                # weekly reports and PDFs
├── slides/weekly/                 # presentation decks
├── docs/                          # roadmap PDF, repo audit, structure notes
├── Research_Papers/               # reference papers (NIPS07 CFR)
└── archive/legacy_before_cleanup/ # superseded files kept for reference
```

### Folder roles

- `poker_ai/agents/`: bot implementations and solvers (baselines, regret matching, CFR).
- `poker_ai/env/`: toy game definitions (RPS payoff matrix).
- `poker_ai/evaluation/`: tournament, duplicate-pair evaluation, exploitability, statistics.
- `experiments/`: runnable weekly-deliverable experiment scripts (run from repo root).
- `scripts/`: utility scripts for smoke tests, reports, demos, and validation.
- `results/tables/`, `results/figures/`: CSV tables and PNG plots committed as deliverables.
- `results/logs/`: generated logs and observer transcripts (not tracked).
- `reports/weekly/`, `slides/weekly/`: weekly reports and presentation decks.
- `docs/`: roadmap, repo audit, and structure documentation (see `docs/repo_structure.md`).
- `archive/legacy_before_cleanup/`: superseded files preserved during repo cleanup.
- `tests/`: sanity tests for agents, tournament logic, regret matching, and CFR.

---

## 6. Status by Week

### Week 4 (part 2): MCCFR — outcome sampling and external sampling

Implements both sampling schemes from Lanctot et al., NIPS 2009
(`Research_Papers/MCCFR_Lanctot2009.pdf`), in `poker_ai/agents/mccfr_outcome.py`
and `poker_ai/agents/mccfr_external.py`:

- **Sampled counterfactual value** (Eq. 6): partition terminal histories into
  blocks Q sampled with probability q; dividing each sampled utility by q(z)
  makes the estimate unbiased (Lemma 1), so regret updates match CFR
  **in expectation** while touching only a fraction of the tree per iteration.
- **Outcome sampling (OS-MCCFR)**: each block is a single terminal history,
  sampled with an epsilon-greedy profile at the update player's infosets
  (`sigma' = eps*uniform + (1-eps)*sigma`, eps = 0.6 per the paper) and
  on-policy elsewhere; epsilon keeps q(z) >= delta > 0, which appears as a
  1/delta factor in the regret bound (Theorem 5).
- **External sampling (ES-MCCFR)**: samples only the choices *external* to the
  update player (chance and opponent); q(z) = pi_{-i}(z) cancels the
  counterfactual weight exactly, giving the clean update r(I,a) += u(a) - u
  (Eq. 11). Needs only a constant factor more iterations than vanilla CFR at
  ~O(sqrt(|H|)) cost per iteration (Theorem 4) — an asymptotic win.

The comparison experiment (`exp04b`) reproduces the paper's Figure-1-style
plot: average-strategy exploitability vs **nodes touched** for vanilla CFR,
CFR+, OS-MCCFR, and ES-MCCFR, plus per-iteration and per-second views.
Validated against OpenSpiel's `OutcomeSamplingSolver` and
`ExternalSamplingSolver` (`scripts/validate_week4b.py`).

### Week 4 (part 1): CFR+ on Kuhn Poker

Implements CFR+ from Tammelin 2014 (`Research_Papers/CFRplus_Tammelin2014.pdf`)
in `poker_ai/agents/cfr_plus.py`. CFR+ changes three things vs vanilla CFR:

1. **Regret-matching+**: cumulative regrets are floored at zero after every
   update, `R+[I][a] <- max(R+[I][a] + (v(a) - v), 0)`, so the next strategy is
   directly proportional to the stored (non-negative) regrets.
2. **Alternating updates**: each iteration runs one pass per player; the pass
   for player i updates only i's regrets and accumulates the opponent's
   average-strategy contribution.
3. **Linear weighted averaging**: strategy contributions on iteration t are
   weighted by `w_t = max(t - d, 0)` (delay `d = 0` by default).

Headline results on Kuhn at 10,000 iterations (exp04):

| Metric | CFR | CFR+ |
|---|---:|---:|
| Average-strategy exploitability | 2.3e-03 | 9.1e-06 (**~255x better**) |
| Current-strategy exploitability | 1.5e-01 (oscillates) | 8.5e-03 (decays) |
| Game value (player 0) | — | -0.055556 = -1/18 exactly |

The recovered CFR+ average strategy lands exactly in the Kuhn Nash family:
alpha = P(bet|J) = 0.2226, P(bet|Q) = 0, P(bet|K) = 0.6678 = 3*alpha.
Validated against OpenSpiel's `CFRPlusSolver` (`scripts/validate_week4.py`).
Also reproduced the paper's compressibility claim: a large fraction of CFR+
regret entries stay exactly zero, while CFR accumulates negative regret.

### Week 2: Regret Matching on Rock-Paper-Scissors

- `RegretMatchingAgent` with two update rules:
  - `update()`: sampled-action regret update (baseline = realized action utility),
  - `update_expected()`: expected-utility update against the opponent's full
    strategy distribution (baseline = own expected utility). The Week 2
    experiment uses the expected-utility rule, with a small seeded random
    regret initialization to break the uniform-strategy fixed point.
- Average strategy converges to the Nash equilibrium (1/3, 1/3, 1/3).
- Plots: average-strategy convergence and average-regret decay (log-log), 5 seeds.

### Week 3: Vanilla CFR on Kuhn Poker

- From-scratch tabular `VanillaCFR` (simultaneous-update, frozen regret tables).
- Exploitability tracked per iteration and validated against OpenSpiel's `CFRSolver`.
- Paper-style payoff cross-table: 5 baselines + our CFR + OpenSpiel CFR.

### Week 1: Setup and baselines

Week 1 built the initial experimental pipeline.

Implemented:

- OpenSpiel smoke test.
- Kuhn Poker baseline tournament.
- Five baseline agents:
  - Random Agent
  - Always-Call Agent
  - Always-Fold Agent
  - Rule-Based Agent
  - EV-Heuristic Agent
- Duplicate-pair match evaluation.
- Multi-seed round-robin tournament.
- CSV result generation.
- Observer transcript script for one OpenSpiel hand.
- Week 1 report and presentation.

The Week 1 tournament uses a round-robin across five agents. With five agents, there are 10 pairwise matchups.

---

## 7. Baseline Agents

### Random Agent

Chooses uniformly among OpenSpiel's legal actions.

Purpose:

- lowest nontrivial baseline,
- tests the action interface,
- any useful agent should beat it.

### Always-Call Agent

Chooses the aggressive/continuing action when possible.

Purpose:

- degenerate over-aggressive baseline,
- easy to exploit,
- useful for checking whether stronger bots punish obvious mistakes.

### Always-Fold Agent

Chooses the passive/folding action when possible.

Purpose:

- degenerate passive baseline,
- useful for debugging payoff signs,
- should be exploited by active strategies.

### Rule-Based Agent

Uses hand-coded poker logic.

Current Kuhn-style heuristic:

| Card | No bet pending | Facing bet |
|---|---|---|
| Jack | pass/check | fold/pass |
| Queen | pass/check | call |
| King | bet | call |

Purpose:

- first domain-knowledge bot,
- interpretable,
- bridges trivial agents and EV/CFR logic.

### EV-Heuristic Agent

Uses expected-value-inspired behavior and may mix with medium-strength hands.

Purpose:

- more principled than fixed rules,
- introduces payoff-based decision-making,
- serves as the strongest simple baseline before regret minimization.

---

## 8. Evaluation Protocol

The main Week 1 metric is **mean payoff to Agent A**.

For each matchup:

1. Agent A plays Agent B.
2. The same deal is replayed with seats swapped.
3. Agent A's payoff is averaged across both seat positions.
4. This is repeated for many duplicate pairs.

This is called duplicate-pair evaluation.

### Why duplicate pairs?

Poker has high variance because card deals matter. Duplicate-pair evaluation reduces card-luck and seat-position variance by forcing both agents to experience the same deal from both seats.

If `n_duplicate_pairs = 10000`, then the actual number of hands is 20,000 because each duplicate pair contains two hands.

---

## 9. Seeds and Reproducibility

A seed fixes randomness so the experiment can be reproduced.

There are two sources of randomness:

1. Game/chance randomness: card deals sampled from OpenSpiel chance outcomes.
2. Agent randomness: stochastic decisions by agents such as Random Agent and EV-Heuristic Agent.

In the tournament evaluator, each experimental seed receives a large non-overlapping block of deal seeds:

```python
base_seed = int(seed) * 1_000_000
deal_seed = base_seed + k
```

Example with `n_pairs = 10000`:

| Experimental seed | Deal seed block |
|---:|---|
| `0` | `0` to `9999` |
| `1` | `1000000` to `1009999` |
| `2` | `2000000` to `2009999` |
| `3` | `3000000` to `3009999` |
| `4` | `4000000` to `4009999` |

This avoids overlap between seeded runs.

---

## 10. Metrics

The result CSV contains one row per matchup per seed.

Important columns:

| Column | Meaning |
|---|---|
| `game` | OpenSpiel game name, e.g. `kuhn_poker` |
| `seed` | experimental repetition seed |
| `agent_a` | first bot in matchup |
| `agent_b` | second bot in matchup |
| `n_duplicate_pairs` | number of duplicate pairs |
| `mean_payoff_to_a` | average payoff to Agent A |
| `ci_low`, `ci_high` | approximate 95% confidence interval for mean payoff |
| `std` | standard deviation of duplicate-pair payoffs |
| `win_rate_a` | fraction of duplicate pairs where Agent A payoff is positive |
| `p_value_vs_zero` | test of whether mean payoff differs from zero |

### Interpreting mean payoff

| Value | Meaning |
|---:|---|
| positive | Agent A beats Agent B on average |
| negative | Agent A loses to Agent B on average |
| near zero | matchup is roughly even |

Mean payoff is more important than win rate because poker payoffs are not all equal-sized. A bot can win many small pots but lose fewer large pots and still be worse overall.

---

## 11. Setup

### Requirements

Recommended:

- Windows 10/11
- Python 3.11 or 3.12
- Git
- VS Code
- Python extension for VS Code
- LaTeX distribution if compiling reports/slides locally

Python packages are listed in `requirements.txt`.

Typical dependencies include:

- `open_spiel`
- `numpy`
- `pandas`
- `matplotlib`
- `pyyaml`
- `tqdm`
- `scipy`
- `pytest`
- `tabulate`

### Create virtual environment

From the project root:

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -e .
```

In PowerShell, activate with:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Select VS Code interpreter

Open VS Code in the project root:

```cmd
code .
```

Then select:

```text
Ctrl + Shift + P
Python: Select Interpreter
<repo root>\.venv\Scripts\python.exe
```

---

## 12. How to Run

### OpenSpiel smoke test

```cmd
python scripts\smoke_test_openspiel.py
```

### Run tests

```cmd
pytest -q
```

### Run Week 1 tournament

Small run:

```cmd
python experiments\exp01_baseline_tournament.py --game kuhn_poker --n-pairs 1000 --seeds 0
```

Full Week 1 run:

```cmd
python experiments\exp01_baseline_tournament.py --game kuhn_poker --n-pairs 10000 --seeds 0 1 2 3 4
```

Output:

```text
results/tables/exp01_baseline_tournament.csv
```

### Generate Week 1 report

```cmd
python scripts\make_week01_report.py
```

Output:

```text
reports/weekly/week01.md
```

### Run Week 2 RPS regret matching (one run per seed)

```cmd
python experiments\exp02_rps_convergence.py --seed 0 --iterations 100000
python experiments\exp02_rps_convergence.py --seed 1 --iterations 100000
python experiments\exp02_rps_convergence.py --seed 2 --iterations 100000
python experiments\exp02_rps_convergence.py --seed 3 --iterations 100000
python experiments\exp02_rps_convergence.py --seed 4 --iterations 100000
```

Outputs:

```text
results/tables/exp02_rps_convergence_seed{N}.csv
results/figures/week02_rps_average_strategy_seed{N}.png
results/figures/week02_rps_average_regret_seed{N}.png
```

### Run Week 3 CFR experiments

```cmd
:: 1) Validate our CFR against OpenSpiel
python scripts\validate_week3.py --game kuhn_poker --iters 1000

:: 2) Convergence CSV + exploitability plot
python experiments\exp03_train_cfr.py --game kuhn_poker --iters 10000

:: 3) Paper-style payoff cross-table
python experiments\exp03_week3_tournament.py --game kuhn_poker --cfr-iters 10000 --n-pairs 10000 --seeds 0 1 2 3 4
```

For a fast smoke run, use `--iters 500 --cfr-iters 500 --n-pairs 1000`.

Outputs:

```text
results/tables/week03_cfr_convergence.csv
results/figures/week03_cfr_convergence.png
results/tables/week03_payoff_matrix.csv
results/tables/week03_pairwise_with_ci.csv
results/figures/week03_payoff_matrix.png
```

### Run Week 4 CFR vs CFR+ comparison

```cmd
:: 1) Validate our CFR+ against OpenSpiel's CFRPlusSolver
python scripts\validate_week4.py --game kuhn_poker --iters 1000

:: 2) Full comparison: exploitability (avg + current), per-second curves,
::    zero-regret fraction, current-strategy Nash convergence
python experiments\exp04_cfr_variants_kuhn.py --game kuhn_poker --iters 10000 --delay 0
```

Outputs:

```text
results/tables/week04_cfr_vs_cfrplus.csv
results/figures/week04_exploitability_vs_iterations.png
results/figures/week04_exploitability_vs_time.png
results/figures/week04_zero_regret_fraction.png
results/figures/week04_current_strategy_trace.png
```

### Run Week 4 MCCFR comparison (CFR vs CFR+ vs OS-MCCFR vs ES-MCCFR)

```cmd
:: 1) Validate our MCCFR solvers against OpenSpiel's
python scripts\validate_week4b.py --os-iters 100000 --es-iters 20000

:: 2) Four-way comparison (paper-style nodes-touched plot + per-iteration + per-second)
python experiments\exp04b_mccfr_kuhn.py --iters 10000 --os-iters 200000 --es-iters 50000 --seeds 0 1 2
```

Outputs:

```text
results/tables/week04b_mccfr_comparison.csv
results/figures/week04b_exploitability_vs_nodes.png
results/figures/week04b_exploitability_vs_iterations.png
results/figures/week04b_exploitability_vs_time.png
```

### Observe one hand step-by-step

```cmd
python scripts\observe_openspiel_game.py --game kuhn_poker --agent-a random --agent-b always_call --seed 0
```

Output:

```text
results/logs/observe_kuhn_poker_random_vs_always_call_seed0.txt
```

This transcript shows the OpenSpiel functions being used: chance outcomes, legal actions, information states, observations, actions, and final returns.

---

## 13. Roadmap

### Week 1: Setup and baselines — DONE

- Set up OpenSpiel.
- Implement baseline agents.
- Run Kuhn Poker tournament.
- Produce reports and slides.

### Week 2: Regret Matching — DONE

- Implement regret matching on Rock-Paper-Scissors (expected-utility updates).
- Plot average strategy convergence.
- Plot regret decay.

### Week 3: Vanilla CFR on Kuhn Poker — DONE

- Implement CFR from scratch.
- Track exploitability.
- Validate against OpenSpiel's CFR solver.

### Week 4: CFR+ and Outcome-Sampling MCCFR — DONE

- Implement CFR+. — DONE
- Implement outcome-sampling MCCFR. — DONE
- Compare convergence curves. — DONE (4-way overlay incl. ES-MCCFR, done early from Week 5)

### Week 5: External-Sampling MCCFR and Leduc Poker — ES-MCCFR DONE EARLY

- Implement external-sampling MCCFR. — DONE (with Week 4)
- Refactor solvers to work beyond Kuhn. — solvers already take any 2p pyspiel.Game
- Run Leduc Poker experiments. — NEXT

### Week 6: Evaluation Suite and Visualizations

- Full tournament suite.
- Paired confidence intervals.
- Strategy visualizations.
- Optional NFSP experiment.

### Week 7: Final Write-Up and Presentation

- Regenerate final plots.
- Freeze results.
- Prepare final report and presentation.

### Week 8: Buffer / Stretch

- Optional Deep CFR / NFSP.
- Polish repository.

---

## 14. Minimum Successful Project

The minimum successful project includes:

- working OpenSpiel pipeline,
- five baseline agents,
- regret matching on RPS,
- Vanilla CFR on Kuhn validated against OpenSpiel,
- CFR+ on Kuhn,
- outcome-sampling and external-sampling MCCFR on Kuhn,
- ES-MCCFR on Leduc,
- tournament table with paired confidence intervals,
- final report and presentation.

Stretch goals include NFSP, Deep CFR, strategy heatmaps, and stronger Leduc experiments.

---

## 15. Out of Scope

The core project does not attempt:

- full Texas Hold'em,
- no-limit poker,
- card abstraction,
- action abstraction,
- real-time subgame solving,
- multi-player poker,
- opponent modeling.

These are future-work topics.

---

## 16. Git Workflow

Check status:

```cmd
git status
```

Stage files:

```cmd
git add .
```

Commit:

```cmd
git commit -m "Describe the change"
```

Push:

```cmd
git push
```

For PDFs or logs that are ignored, force-add carefully:

```cmd
git add -f path\to\file.pdf
```

---

## 17. Notes for Readers

This repository is written as a research-learning project. The code is intentionally modular and heavily documented so that each step can be explained to a professor or reviewer.

The main conceptual progression is:

```text
environment setup
→ baseline agents
→ regret matching
→ vanilla CFR
→ CFR+
→ MCCFR
→ Leduc scaling
→ final evaluation
```

The Week 1 results are not meant to prove that any bot is strong. They prove that the environment, agents, tournament evaluator, statistics, reports, and Git workflow are working correctly.
