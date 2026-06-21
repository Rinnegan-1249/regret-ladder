// Live-training SSE consumers for the RPS and Kuhn pages.
// Streams carry BOTH players' data; the player toggle just re-renders.

// Shared dark Plotly layout matching the site theme.
function darkLayout(overrides) {
  return Object.assign({
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "JetBrains Mono, monospace", size: 11.5, color: "#8b96ab" },
    title: { font: { family: "Space Grotesk, sans-serif", size: 15, color: "#e6ebf5" } },
    xaxis: { gridcolor: "rgba(255,255,255,0.07)", zerolinecolor: "rgba(255,255,255,0.12)" },
    yaxis: { gridcolor: "rgba(255,255,255,0.07)", zerolinecolor: "rgba(255,255,255,0.12)" },
    legend: { bgcolor: "rgba(0,0,0,0)" },
    margin: { t: 46, r: 20, b: 50, l: 60 },
    height: 400,
  }, overrides || {});
}

function mergeAxes(layout, x, y) {
  layout.xaxis = Object.assign({}, layout.xaxis, x);
  layout.yaxis = Object.assign({}, layout.yaxis, y);
  return layout;
}

const PLOT_CONFIG = { displayModeBar: false, responsive: true };

// In static (GitHub Pages) builds there's no SSE server: fetch a precomputed
// checkpoint-array JSON once and replay it on the same onEvent/onDone/onError
// callbacks consumeSSE uses, so the render functions below don't need to
// know which transport is active. Falls back to the live SSE endpoint
// otherwise. Returns a controller with .abort(), like consumeSSE.
function startReplayOrLive(liveUrl, staticUrl, onEvent, onDone, onError) {
  if (window.STATIC_MODE) {
    let aborted = false;
    let inner = null;
    fetch(`${window.SITE_BASE || ""}${staticUrl}`)
      .then((r) => r.json())
      .then((data) => { if (!aborted) inner = replayCheckpoints(data.events, onEvent, onDone); })
      .catch((err) => { if (!aborted && onError) onError(err); });
    return { abort: () => { aborted = true; if (inner) inner.abort(); } };
  }
  return consumeSSE(liveUrl, onEvent, onDone, onError);
}

// Leduc training has no live SSE counterpart at all (see web/templates/leduc.html) —
// it always replays a precomputed checkpoint array fetched from staticUrl.
function replayCheckpointsFromUrl(staticUrl, onEvent, onDone, onError) {
  let aborted = false;
  let inner = null;
  fetch(`${window.SITE_BASE || ""}${staticUrl}`)
    .then((r) => r.json())
    .then((data) => { if (!aborted) inner = replayCheckpoints(data.events, onEvent, onDone); })
    .catch((err) => { if (!aborted && onError) onError(err); });
  return { abort: () => { aborted = true; if (inner) inner.abort(); } };
}

(() => {
  const el = (id) => document.getElementById(id);

  /* ---------------- RPS live training ---------------- */
  if (el("rps-train-start")) {
    let data = { t: [], p1: [[], [], []], p2: [[], [], []], r1: [], r2: [] };
    let stream = null;

    function rpsStrategyLayout(player) {
      return mergeAxes(darkLayout({ title: { text: `Average strategy convergence — Player ${player}` } }),
        { type: "log", title: { text: "Iteration" } },
        { title: { text: "Probability" }, range: [0, 1] });
    }
    function rpsRegretLayout() {
      return mergeAxes(darkLayout({ title: { text: "Average regret decay (log–log)" }, height: 320 }),
        { type: "log", title: { text: "Iteration" } },
        { type: "log", title: { text: "R_T / T" } });
    }

    function renderRps() {
      try {
        const player = el("rps-train-player").value;
        const avg = player === "1" ? data.p1 : data.p2;
        const names = ["rock", "paper", "scissors"];
        const colors = ["#38bdf8", "#34e3a4", "#fbbf24"];
        // IMPORTANT: pass fresh copies (.slice()) — Plotly.react compares by
        // reference, so arrays mutated in place with push() are treated as
        // unchanged and the chart never redraws.
        const traces = names.map((n, i) => ({
          x: data.t.slice(), y: avg[i].slice(), mode: "lines", name: `P${player} avg ${n}`,
          line: { color: colors[i], width: 2 },
        }));
        traces.push({
          x: [1, data.t[data.t.length - 1] || 10], y: [1 / 3, 1 / 3], mode: "lines",
          name: "Nash = 1/3", line: { dash: "dash", color: "#8b96ab", width: 1.5 },
        });
        Plotly.react("rps-strategy-chart", traces, rpsStrategyLayout(player), PLOT_CONFIG);
        Plotly.react("rps-regret-chart",
          [{ x: data.t.slice(), y: data.r1.slice(), mode: "lines", name: "P1 avg regret", line: { color: "#34e3a4", width: 2 } },
           { x: data.t.slice(), y: data.r2.slice(), mode: "lines", name: "P2 avg regret", line: { color: "#38bdf8", width: 2 } }],
          rpsRegretLayout(), PLOT_CONFIG);
      } catch (err) {
        setStatus(el("rps-train-status"), `Chart error: ${err.message}`, true);
      }
    }

    // Placeholder axes so the pane never looks empty.
    function placeholders() {
      Plotly.react("rps-strategy-chart", [], rpsStrategyLayout(el("rps-train-player").value), PLOT_CONFIG);
      Plotly.react("rps-regret-chart", [], rpsRegretLayout(), PLOT_CONFIG);
    }
    window.rpsTrainPlaceholders = () => { if (!data.t.length) placeholders(); };

    el("rps-train-player").addEventListener("change", renderRps);

    el("rps-train-start").addEventListener("click", () => {
      if (stream) stream.abort();
      data = { t: [], p1: [[], [], []], p2: [[], [], []], r1: [], r2: [] };
      const T = +el("rps-train-T").value, seed = +el("rps-train-seed").value;
      let total = T; // overwritten by the "start" event - matters in static
                      // mode, where the replay's actual iteration count is
                      // fixed by the precomputed file, not this input.
      setStatus(el("rps-train-status"),
        window.STATIC_MODE ? "Replaying precomputed training run…" : "Training…");
      stream = startReplayOrLive(
        `/api/train/rps/stream?iterations=${T}&seed=${seed}`,
        "/static/data/training/rps.json",
        (ev) => {
          if (ev.type === "start") { total = ev.iterations || total; return; }
          if (ev.type !== "checkpoint") return;
          data.t.push(ev.t);
          for (let i = 0; i < 3; i++) { data.p1[i].push(ev.p1_avg[i]); data.p2[i].push(ev.p2_avg[i]); }
          data.r1.push(Math.max(ev.p1_avg_regret, 1e-12));
          data.r2.push(Math.max(ev.p2_avg_regret, 1e-12));
          renderRps();
          setStatus(el("rps-train-status"), `Iteration ${ev.t.toLocaleString()} / ${total.toLocaleString()}`);
        }, () => {
          renderRps();
          setStatus(el("rps-train-status"), "Done — strategies converged toward (1/3, 1/3, 1/3).");
        }, (err) => setStatus(el("rps-train-status"), err.message, true));
    });
  }

  /* ---------------- Kuhn live training ---------------- */
  if (el("kuhn-train-start")) {
    const CAPS = { cfr: 10000, cfr_plus: 10000, os_mccfr: 200000, es_mccfr: 50000 };
    let kd = { t: [], expl: [], infosets: { p1: {}, p2: {} } };
    let stream = null;

    el("kuhn-train-algo").addEventListener("change", () => {
      const cap = CAPS[el("kuhn-train-algo").value];
      el("kuhn-train-T").max = cap;
      if (+el("kuhn-train-T").value > cap) el("kuhn-train-T").value = cap;
      el("kuhn-train-cap").textContent = `(max ${cap.toLocaleString()})`;
    });

    function infosetLabel(info) {
      const cards = { 0: "J", 1: "Q", 2: "K" };
      const betting = info.slice(1);
      return `${cards[info[0]]}${betting ? " after '" + betting + "'" : " (opening)"}`;
    }

    function kuhnStrategyLayout(player) {
      return mergeAxes(darkLayout({
        title: { text: `Average strategy: P(bet/call) at Player ${player}'s information sets` } }),
        { type: "log", title: { text: "Iteration" } },
        { title: { text: "P(bet/call)" }, range: [-0.02, 1.02] });
    }
    function kuhnExplLayout() {
      return mergeAxes(darkLayout({ title: { text: "Exploitability of the average strategy (log–log)" }, height: 320 }),
        { type: "log", title: { text: "Iteration" } },
        { type: "log", title: { text: "Exploitability" } });
    }

    const ISET_COLORS = ["#34e3a4", "#38bdf8", "#fbbf24", "#f87171", "#c084fc", "#fb923c"];

    function renderKuhn() {
      try {
        const player = el("kuhn-train-player").value;
        const sets = kd.infosets[`p${player}`];
        // Fresh copies for the same Plotly.react reference-equality reason.
        const traces = Object.keys(sets).sort().map((info, i) => ({
          x: kd.t.slice(), y: sets[info].slice(), mode: "lines", name: infosetLabel(info),
          line: { color: ISET_COLORS[i % ISET_COLORS.length], width: 2 },
        }));
        Plotly.react("kuhn-strategy-chart", traces, kuhnStrategyLayout(player), PLOT_CONFIG);
        Plotly.react("kuhn-expl-chart",
          [{ x: kd.t, y: kd.expl.map((e) => Math.max(e, 1e-12)), mode: "lines",
             name: "exploitability", line: { color: "#34e3a4", width: 2 } }],
          kuhnExplLayout(), PLOT_CONFIG);
      } catch (err) {
        setStatus(el("kuhn-train-status"), `Chart error: ${err.message}`, true);
      }
    }

    function placeholders() {
      Plotly.react("kuhn-strategy-chart", [], kuhnStrategyLayout(el("kuhn-train-player").value), PLOT_CONFIG);
      Plotly.react("kuhn-expl-chart", [], kuhnExplLayout(), PLOT_CONFIG);
    }
    window.kuhnTrainPlaceholders = () => { if (!kd.t.length) placeholders(); };

    el("kuhn-train-player").addEventListener("change", renderKuhn);

    el("kuhn-train-start").addEventListener("click", () => {
      if (stream) stream.abort();
      kd = { t: [], expl: [], infosets: { p1: {}, p2: {} } };
      const algo = el("kuhn-train-algo").value;
      const T = +el("kuhn-train-T").value, seed = +el("kuhn-train-seed").value;
      let total = T; // see RPS block above - overwritten by the "start" event.
      setStatus(el("kuhn-train-status"),
        window.STATIC_MODE ? "Replaying precomputed training run…" : "Training…");
      stream = startReplayOrLive(
        `/api/train/kuhn/stream?algo=${algo}&iterations=${T}&seed=${seed}`,
        `/static/data/training/kuhn_${algo}.json`,
        (ev) => {
        if (ev.type === "start") { total = ev.iterations || total; return; }
        if (ev.type !== "checkpoint") return;
        kd.t.push(ev.t);
        kd.expl.push(ev.exploitability);
        for (const p of ["p1", "p2"]) {
          for (const [info, prob] of Object.entries(ev.bet_probs[p])) {
            if (!kd.infosets[p][info]) kd.infosets[p][info] = new Array(kd.t.length - 1).fill(null);
            kd.infosets[p][info].push(prob);
          }
          for (const arr of Object.values(kd.infosets[p])) {
            while (arr.length < kd.t.length) arr.push(arr[arr.length - 1]);
          }
        }
        renderKuhn();
        setStatus(el("kuhn-train-status"),
          `Iteration ${ev.t.toLocaleString()} / ${total.toLocaleString()} — exploitability ${ev.exploitability.toExponential(2)}`);
      }, () => {
        renderKuhn();
        setStatus(el("kuhn-train-status"), "Done.");
      }, (err) => setStatus(el("kuhn-train-status"), err.message, true));
    });
  }

  /* ---------------- Leduc training replay (always precomputed) ---------------- */
  if (el("leduc-train-start")) {
    let ld = { t: [], cfrExpl: [], cfrplusExpl: [], cfrZero: [], cfrplusZero: [] };
    let stream = null;

    function leducExplLayout() {
      return mergeAxes(darkLayout({ title: { text: "Exploitability of the average strategy (log–log)" } }),
        { type: "log", title: { text: "Iteration" } },
        { type: "log", title: { text: "Exploitability" } });
    }
    function leducZeroRegLayout() {
      return mergeAxes(darkLayout({ title: { text: "Fraction of regret entries exactly zero" }, height: 320 }),
        { type: "log", title: { text: "Iteration" } },
        { title: { text: "Fraction" }, range: [0, 1] });
    }

    function renderLeduc() {
      try {
        Plotly.react("leduc-expl-chart", [
          { x: ld.t.slice(), y: ld.cfrExpl.slice(), mode: "lines", name: "CFR", line: { color: "#f87171", width: 2 } },
          { x: ld.t.slice(), y: ld.cfrplusExpl.slice(), mode: "lines", name: "CFR+", line: { color: "#34e3a4", width: 2 } },
        ], leducExplLayout(), PLOT_CONFIG);
        Plotly.react("leduc-zeroreg-chart", [
          { x: ld.t.slice(), y: ld.cfrZero.slice(), mode: "lines", name: "CFR", line: { color: "#f87171", width: 2 } },
          { x: ld.t.slice(), y: ld.cfrplusZero.slice(), mode: "lines", name: "CFR+", line: { color: "#34e3a4", width: 2 } },
        ], leducZeroRegLayout(), PLOT_CONFIG);
      } catch (err) {
        setStatus(el("leduc-train-status"), `Chart error: ${err.message}`, true);
      }
    }

    function placeholders() {
      Plotly.react("leduc-expl-chart", [], leducExplLayout(), PLOT_CONFIG);
      Plotly.react("leduc-zeroreg-chart", [], leducZeroRegLayout(), PLOT_CONFIG);
    }
    window.leducTrainPlaceholders = () => { if (!ld.t.length) placeholders(); };

    el("leduc-train-start").addEventListener("click", () => {
      if (stream) stream.abort();
      ld = { t: [], cfrExpl: [], cfrplusExpl: [], cfrZero: [], cfrplusZero: [] };
      setStatus(el("leduc-train-status"), "Replaying the validated 10,000-iteration training run…");
      stream = replayCheckpointsFromUrl("/static/data/training/leduc.json", (ev) => {
        if (ev.type !== "checkpoint") return;
        ld.t.push(ev.t);
        ld.cfrExpl.push(Math.max(ev.cfr_expl, 1e-12));
        ld.cfrplusExpl.push(Math.max(ev.cfrplus_expl, 1e-12));
        ld.cfrZero.push(ev.cfr_zero_regret_frac);
        ld.cfrplusZero.push(ev.cfrplus_zero_regret_frac);
        renderLeduc();
        setStatus(el("leduc-train-status"), `Iteration ${ev.t.toLocaleString()} / 10,000`);
      }, () => {
        renderLeduc();
        setStatus(el("leduc-train-status"), "Done.");
      }, (err) => setStatus(el("leduc-train-status"), err.message, true));
    });
  }
})();
