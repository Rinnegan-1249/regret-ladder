# Poker Project

This project is built around OpenSpiel, beginning with simple baseline agents on Kuhn Poker and progressing toward regret-minimization methods such as Regret Matching, Vanilla CFR, CFR+, and Monte Carlo CFR.

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
poker-ai/
├── README.md
├── pyproject.toml
├── requirements.txt
├── poker_ai/
│   ├── agents/
│   │   ├── base.py
│   │   ├── random_agent.py
│   │   ├── always_call.py
│   │   ├── always_fold.py
│   │   ├── rule_based.py
│   │   └── ev_heuristic.py
│   ├── evaluation/
│   │   ├── tournament.py
│   │   └── stats.py
│   └── utils/
│       └── seeding.py
├── experiments/
│   └── exp01_baseline_tournament.py
├── scripts/
│   ├── smoke_test_openspiel.py
│   ├── observe_openspiel_game.py
│   └── make_week01_report.py
├── results/
│   ├── tables/
│   └── logs/
├── reports/
│   └── weekly/
├── slides/
│   └── weekly/
├── docs/
│   └── week01/
└── tests/
```

### Folder roles

- `poker_ai/agents/`: bot implementations.
- `poker_ai/evaluation/`: tournament, duplicate-pair evaluation, statistics.
- `experiments/`: runnable experiment scripts.
- `scripts/`: utility scripts for smoke tests, reports, and observing a single hand.
- `results/tables/`: CSV result tables.
- `results/logs/`: generated logs and observer transcripts.
- `reports/weekly/`: weekly reports and PDFs.
- `slides/weekly/`: weekly presentation decks and PDFs.
- `docs/week01/`: detailed explanatory notes, longer than weekly reports.
- `tests/`: sanity tests for agents and tournament logic.

---

## 6. Week 1 Status

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
C:\Users\hp\Desktop\poker-ai-week1-starter\.venv\Scripts\python.exe
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

### Week 1: Setup and baselines

- Set up OpenSpiel.
- Implement baseline agents.
- Run Kuhn Poker tournament.
- Produce reports and slides.

### Week 2: Regret Matching

- Implement regret matching on Rock-Paper-Scissors.
- Plot average strategy convergence.
- Plot regret decay.

### Week 3: Vanilla CFR on Kuhn Poker

- Implement CFR from scratch.
- Track exploitability.
- Validate against OpenSpiel's CFR solver.

### Week 4: CFR+ and Outcome-Sampling MCCFR

- Implement CFR+.
- Implement outcome-sampling MCCFR.
- Compare convergence curves.

### Week 5: External-Sampling MCCFR and Leduc Poker

- Implement external-sampling MCCFR.
- Refactor solvers to work beyond Kuhn.
- Run Leduc Poker experiments.

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
