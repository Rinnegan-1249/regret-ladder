// Client-side RPS match engine for the static (GitHub Pages) build.
//
// Pure-JS port of web/rps_engine.py + poker_ai/agents/regret_matching.py +
// poker_ai/env/rps.py. RPS has zero OpenSpiel dependency (unlike Kuhn/Leduc's
// CFR family), so this can faithfully run client-side with no precomputation
// beyond the already-cached frozen strategy. Only active when
// window.STATIC_MODE is true; rps.js falls back to the live /api/rps/* server
// endpoints otherwise.

const ACTION_NAMES_JS = ["rock", "paper", "scissors"];
const PAYOFF_MATRIX_JS = [
  [0, -1, 1],
  [1, 0, -1],
  [-1, 1, 0],
];

function rpsPayoff(a, b) {
  return PAYOFF_MATRIX_JS[a][b];
}

function rpsUtilitiesAgainst(oppAction) {
  return [PAYOFF_MATRIX_JS[0][oppAction], PAYOFF_MATRIX_JS[1][oppAction], PAYOFF_MATRIX_JS[2][oppAction]];
}

// Deterministic seeded PRNG (mulberry32) so static-mode matches are
// reproducible from a seed exactly like the server's np.random.default_rng.
function mulberry32(seed) {
  let s = seed >>> 0;
  return function () {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function sampleFromDist(probs, rng) {
  const r = rng();
  let cum = 0;
  for (let i = 0; i < probs.length; i++) {
    cum += probs[i];
    if (r < cum) return i;
  }
  return probs.length - 1;
}

// Port of poker_ai.agents.regret_matching.RegretMatchingAgent (update() +
// current_strategy() only — the realized-action update used by the
// adaptive seat in play mode).
class RmAgentJS {
  constructor(seed) {
    this.rng = mulberry32(seed);
    this.regretSum = [0, 0, 0];
  }
  currentStrategy() {
    const pos = this.regretSum.map((r) => Math.max(r, 0));
    const norm = pos[0] + pos[1] + pos[2];
    if (norm > 0) return pos.map((p) => p / norm);
    return [1 / 3, 1 / 3, 1 / 3];
  }
  update(strategy, action, utilities) {
    const actual = utilities[action];
    for (let a = 0; a < 3; a++) this.regretSum[a] += utilities[a] - actual;
  }
}

// Port of web.rps_engine.RpsMatch.
class RpsMatchJS {
  constructor(matchId, kinds, dists, rounds, seed, frozenStrategy) {
    this.matchId = matchId;
    this.kinds = kinds; // [kind0, kind1]
    this.dists = dists; // [dist0|null, dist1|null]
    this.roundsTotal = rounds;
    this.rng = mulberry32(seed);
    this.frozen = frozenStrategy;
    this.adaptive = {};
    kinds.forEach((k, i) => {
      if (k === "rm_adaptive") this.adaptive[i] = new RmAgentJS(seed + i + 1);
    });
    this.scores = [0, 0];
    this.history = [];
  }

  get roundsPlayed() {
    return this.history.length;
  }
  get finished() {
    return this.roundsPlayed >= this.roundsTotal;
  }
  hasHuman() {
    return this.kinds.includes("human");
  }

  seatAction(i, humanAction) {
    const kind = this.kinds[i];
    if (kind === "human") {
      if (humanAction === null || humanAction === undefined) {
        throw new Error(`Player ${i + 1} is human: an action is required`);
      }
      return [humanAction, null];
    }
    if (kind === "distribution") {
      const d = this.dists[i];
      return [sampleFromDist(d, this.rng), d];
    }
    if (kind === "rm_frozen") {
      return [sampleFromDist(this.frozen, this.rng), this.frozen];
    }
    // rm_adaptive
    const agent = this.adaptive[i];
    const strategy = agent.currentStrategy();
    return [sampleFromDist(strategy, agent.rng), strategy];
  }

  playRound(p1Action, p2Action) {
    if (this.finished) throw new Error("Match already finished");
    const [a1, s1] = this.seatAction(0, p1Action);
    const [a2, s2] = this.seatAction(1, p2Action);
    const u1 = rpsPayoff(a1, a2);
    this.scores[0] += u1;
    this.scores[1] -= u1;

    const strategiesUsed = [s1, s2];
    const oppAction = [a2, a1];
    const acts = [a1, a2];
    for (const key of Object.keys(this.adaptive)) {
      const i = +key;
      const agent = this.adaptive[i];
      agent.update(
        strategiesUsed[i] || agent.currentStrategy(),
        acts[i],
        rpsUtilitiesAgainst(oppAction[i])
      );
    }

    const row = {
      round: this.roundsPlayed + 1,
      p1_action: a1,
      p2_action: a2,
      p1_action_name: ACTION_NAMES_JS[a1],
      p2_action_name: ACTION_NAMES_JS[a2],
      p1_payoff: u1,
      scores: this.scores.slice(),
    };
    for (const key of Object.keys(this.adaptive)) {
      const i = +key;
      row[`p${i + 1}_adaptive_strategy`] = this.adaptive[i].currentStrategy();
    }
    this.history.push(row);
    return row;
  }

  autoRun() {
    if (this.hasHuman()) throw new Error("auto_run is only for matches without a human seat");
    const rows = [];
    while (!this.finished) rows.push(this.playRound(null, null));
    return rows;
  }

  summary() {
    const freqs = [0, 1].map((i) => {
      const counts = [0, 0, 0];
      for (const row of this.history) counts[row[`p${i + 1}_action`]] += 1;
      const total = counts[0] + counts[1] + counts[2];
      return total ? counts.map((c) => c / total) : [0, 0, 0];
    });
    return {
      match_id: this.matchId,
      rounds_played: this.roundsPlayed,
      rounds_total: this.roundsTotal,
      finished: this.finished,
      scores: this.scores.slice(),
      empirical_frequencies: freqs,
      seats: this.kinds.slice(),
    };
  }
}

// ---- API-shaped adapter, mirroring the /api/rps/* endpoints exactly so
// rps.js's UI logic stays unchanged regardless of static vs. live mode.
const RpsClient = (() => {
  let frozenStrategyPromise = null;
  function frozenStrategy() {
    if (!frozenStrategyPromise) {
      frozenStrategyPromise = fetch(`${window.SITE_BASE || ""}/static/data/policies/rps_frozen.json`)
        .then((r) => r.json());
    }
    return frozenStrategyPromise;
  }

  const matches = new Map();
  let nextId = 1;

  async function new_match(body) {
    const frozen = await frozenStrategy();
    const matchId = `static-${nextId++}`;
    const match = new RpsMatchJS(
      matchId,
      [body.p1.kind, body.p2.kind],
      [body.p1.dist || null, body.p2.dist || null],
      body.rounds,
      body.seed,
      frozen
    );
    matches.set(matchId, match);
    return match.summary();
  }

  async function play(matchId, body) {
    const match = matches.get(matchId);
    if (!match) throw new Error("Unknown or expired match id");
    const row = match.playRound(body.p1_action, body.p2_action);
    return { round: row, summary: match.summary() };
  }

  async function auto(matchId) {
    const match = matches.get(matchId);
    if (!match) throw new Error("Unknown or expired match id");
    const rows = match.autoRun();
    return { rounds: rows, summary: match.summary() };
  }

  return { new_match, play, auto };
})();

window.RpsClient = RpsClient;
