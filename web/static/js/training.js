// Live-training SSE consumers for the RPS and Kuhn pages.
// Streams carry BOTH players' data; the player toggle just re-renders.
(() => {
  const el = (id) => document.getElementById(id);

  /* ---------------- RPS live training ---------------- */
  if (el("rps-train-start")) {
    let data = { t: [], p1: [[], [], []], p2: [[], [], []], r1: [], r2: [] };
    let stream = null;

    function renderRps() {
      const player = el("rps-train-player").value;
      const avg = player === "1" ? data.p1 : data.p2;
      const names = ["rock", "paper", "scissors"];
      Plotly.react("rps-strategy-chart",
        names.map((n, i) => ({ x: data.t, y: avg[i], mode: "lines", name: `P${player} avg ${n}` }))
          .concat([{ x: [1, data.t[data.t.length - 1] || 1], y: [1 / 3, 1 / 3],
            mode: "lines", name: "Nash = 1/3", line: { dash: "dash", color: "#888" } }]),
        { title: `Average strategy convergence — Player ${player}`,
          xaxis: { type: "log", title: "Iteration" },
          yaxis: { title: "Probability", range: [0, 1] }, margin: { t: 40 } },
        { displayModeBar: false });
      Plotly.react("rps-regret-chart",
        [{ x: data.t, y: data.r1, mode: "lines", name: "P1 avg regret" },
         { x: data.t, y: data.r2, mode: "lines", name: "P2 avg regret" }],
        { title: "Average regret decay",
          xaxis: { type: "log", title: "Iteration" },
          yaxis: { type: "log", title: "R_T / T" }, margin: { t: 40 } },
        { displayModeBar: false });
    }

    el("rps-train-player").addEventListener("change", renderRps);

    el("rps-train-start").addEventListener("click", () => {
      if (stream) stream.abort();
      data = { t: [], p1: [[], [], []], p2: [[], [], []], r1: [], r2: [] };
      const T = +el("rps-train-T").value, seed = +el("rps-train-seed").value;
      setStatus(el("rps-train-status"), "Training…");
      stream = consumeSSE(`/api/train/rps/stream?iterations=${T}&seed=${seed}`, (ev) => {
        if (ev.type !== "checkpoint") return;
        data.t.push(ev.t);
        for (let i = 0; i < 3; i++) { data.p1[i].push(ev.p1_avg[i]); data.p2[i].push(ev.p2_avg[i]); }
        data.r1.push(Math.max(ev.p1_avg_regret, 1e-12));
        data.r2.push(Math.max(ev.p2_avg_regret, 1e-12));
        renderRps();
        setStatus(el("rps-train-status"), `Iteration ${ev.t.toLocaleString()} / ${T.toLocaleString()}`);
      }, () => setStatus(el("rps-train-status"), "Done."),
         (err) => setStatus(el("rps-train-status"), err.message, true));
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

    function renderKuhn() {
      const player = el("kuhn-train-player").value;
      const sets = kd.infosets[`p${player}`];
      const traces = Object.keys(sets).sort().map((info) => ({
        x: kd.t, y: sets[info], mode: "lines", name: infosetLabel(info),
      }));
      Plotly.react("kuhn-strategy-chart", traces,
        { title: `Average strategy: P(bet/call) at Player ${player}'s information sets`,
          xaxis: { type: "log", title: "Iteration" },
          yaxis: { title: "P(bet/call)", range: [-0.02, 1.02] }, margin: { t: 40 } },
        { displayModeBar: false });
      Plotly.react("kuhn-expl-chart",
        [{ x: kd.t, y: kd.expl.map((e) => Math.max(e, 1e-12)), mode: "lines", name: "exploitability" }],
        { title: "Exploitability of the average strategy",
          xaxis: { type: "log", title: "Iteration" },
          yaxis: { type: "log", title: "Exploitability" }, margin: { t: 40 } },
        { displayModeBar: false });
    }

    el("kuhn-train-player").addEventListener("change", renderKuhn);

    el("kuhn-train-start").addEventListener("click", () => {
      if (stream) stream.abort();
      kd = { t: [], expl: [], infosets: { p1: {}, p2: {} } };
      const algo = el("kuhn-train-algo").value;
      const T = +el("kuhn-train-T").value, seed = +el("kuhn-train-seed").value;
      setStatus(el("kuhn-train-status"), "Training…");
      stream = consumeSSE(`/api/train/kuhn/stream?algo=${algo}&iterations=${T}&seed=${seed}`, (ev) => {
        if (ev.type !== "checkpoint") return;
        kd.t.push(ev.t);
        kd.expl.push(ev.exploitability);
        for (const p of ["p1", "p2"]) {
          for (const [info, prob] of Object.entries(ev.bet_probs[p])) {
            if (!kd.infosets[p][info]) kd.infosets[p][info] = new Array(kd.t.length - 1).fill(null);
            kd.infosets[p][info].push(prob);
          }
          // pad infosets missing from this checkpoint
          for (const arr of Object.values(kd.infosets[p])) {
            while (arr.length < kd.t.length) arr.push(arr[arr.length - 1]);
          }
        }
        renderKuhn();
        setStatus(el("kuhn-train-status"),
          `Iteration ${ev.t.toLocaleString()} / ${T.toLocaleString()} — exploitability ${ev.exploitability.toExponential(2)}`);
      }, () => setStatus(el("kuhn-train-status"), "Done."),
         (err) => setStatus(el("kuhn-train-status"), err.message, true));
    });
  }
})();
