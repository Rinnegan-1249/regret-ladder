// RPS play tab logic.
(() => {
  const tabsRoot = document.getElementById("rps-tabs");
  if (tabsRoot) initTabs(tabsRoot);

  const el = (id) => document.getElementById(id);
  let match = null; // {id, seats, rounds}

  const ACTION_NAMES = ["Rock", "Paper", "Scissors"];

  function distOf(prefix) {
    return [+el(`${prefix}-d0`).value, +el(`${prefix}-d1`).value, +el(`${prefix}-d2`).value];
  }

  function seatLabel(kind) {
    return {
      human: "Human", distribution: "Human (distribution)",
      rm_frozen: "RM bot (frozen 10k)", rm_adaptive: "RM bot (adaptive)",
    }[kind] || kind;
  }

  ["p1", "p2"].forEach((p) => {
    el(`${p}-kind`).addEventListener("change", () => {
      el(`${p}-dist-field`).style.display =
        el(`${p}-kind`).value === "distribution" ? "" : "none";
    });
  });

  function humanSeats() {
    return [0, 1].filter((i) => match.seats[i] === "human");
  }

  function updateScoreboard(summary) {
    el("rps-score1").textContent = summary.scores[0].toFixed(0);
    el("rps-score2").textContent = summary.scores[1].toFixed(0);
    el("rps-roundno").textContent = `${summary.rounds_played} / ${summary.rounds_total}`;
  }

  function appendLog(row) {
    const tbody = el("rps-log").querySelector("tbody");
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${row.round}</td><td>${ACTION_NAMES[row.p1_action]}</td>` +
      `<td>${ACTION_NAMES[row.p2_action]}</td><td>${row.p1_payoff}</td>` +
      `<td>${row.scores[0]} : ${row.scores[1]}</td>`;
    tbody.prepend(tr);
  }

  function showAdaptive(row) {
    const key = match.seats[0] === "rm_adaptive" ? "p1_adaptive_strategy"
      : match.seats[1] === "rm_adaptive" ? "p2_adaptive_strategy" : null;
    if (!key || !row[key]) return;
    el("rps-adaptive-view").style.display = "";
    const bars = el("rps-adaptive-bars");
    bars.innerHTML = "";
    row[key].forEach((p, i) => {
      const bar = document.createElement("div");
      bar.className = "bar";
      bar.style.height = `${Math.max(3, p * 85)}px`;
      bar.title = `${ACTION_NAMES[i]}: ${(p * 100).toFixed(1)}%`;
      bar.innerHTML = `<label>${ACTION_NAMES[i][0]} ${(p * 100).toFixed(0)}%</label>`;
      bars.appendChild(bar);
    });
  }

  function promptNext() {
    const humans = humanSeats();
    if (match.finished) {
      el("rps-actions").style.display = "none";
      setStatus(el("rps-status"),
        `Match finished. Final score ${el("rps-score1").textContent} : ${el("rps-score2").textContent}.`);
      return;
    }
    if (humans.length > 0) {
      el("rps-actions").style.display = "";
      el("rps-prompt").textContent = humans.length === 2
        ? "Hot-seat: Player 1 picks first (P2 looks away!), then Player 2."
        : `You are Player ${humans[0] + 1} — pick your move:`;
    } else {
      el("rps-autorun").style.display = "";
    }
  }

  let pendingP1 = null; // for human-vs-human hot-seat

  async function humanPick(action) {
    const humans = humanSeats();
    try {
      if (humans.length === 2) {
        if (pendingP1 === null) {
          pendingP1 = action;
          el("rps-prompt").textContent = "Player 2's turn — pick your move:";
          return;
        }
        await playRound(pendingP1, action);
        pendingP1 = null;
        el("rps-prompt").textContent = "Player 1 picks first:";
      } else if (humans[0] === 0) {
        await playRound(action, null);
      } else {
        await playRound(null, action);
      }
    } catch (err) {
      setStatus(el("rps-status"), err.message, true);
    }
  }

  async function playRound(a1, a2) {
    const data = await postJSON(`/api/rps/${match.id}/play`, { p1_action: a1, p2_action: a2 });
    appendLog(data.round);
    showAdaptive(data.round);
    updateScoreboard(data.summary);
    match.finished = data.summary.finished;
    setStatus(el("rps-status"),
      `Round ${data.round.round}: ${ACTION_NAMES[data.round.p1_action]} vs ` +
      `${ACTION_NAMES[data.round.p2_action]} — P1 payoff ${data.round.p1_payoff}`);
    promptNext();
  }

  el("rps-start").addEventListener("click", async () => {
    const body = {
      p1: { kind: el("p1-kind").value }, p2: { kind: el("p2-kind").value },
      rounds: +el("rps-rounds").value, seed: Math.floor(Math.random() * 1e6),
    };
    if (body.p1.kind === "distribution") body.p1.dist = distOf("p1");
    if (body.p2.kind === "distribution") body.p2.dist = distOf("p2");
    try {
      const summary = await postJSON("/api/rps/new", body);
      match = { id: summary.match_id, seats: summary.seats, finished: false };
      el("rps-game").style.display = "";
      el("rps-log").querySelector("tbody").innerHTML = "";
      el("rps-autorun").style.display = "none";
      el("rps-actions").style.display = "none";
      el("rps-adaptive-view").style.display = "none";
      el("rps-score-chart").style.display = "none";
      el("rps-who1").textContent = `Player 1 — ${seatLabel(match.seats[0])}`;
      el("rps-who2").textContent = `Player 2 — ${seatLabel(match.seats[1])}`;
      updateScoreboard(summary);
      setStatus(el("rps-status"), "Match started.");
      pendingP1 = null;
      promptNext();
    } catch (err) {
      setStatus(el("rps-status"), err.message, true);
    }
  });

  el("rps-actions").querySelectorAll("button.action").forEach((b) =>
    b.addEventListener("click", () => humanPick(+b.dataset.a)));

  el("rps-autorun").addEventListener("click", async () => {
    try {
      el("rps-autorun").disabled = true;
      const data = await postJSON(`/api/rps/${match.id}/auto`);
      data.rounds.forEach(appendLog);
      if (data.rounds.length) showAdaptive(data.rounds[data.rounds.length - 1]);
      updateScoreboard(data.summary);
      match.finished = true;
      // Cumulative score chart
      const cum = [];
      let s = 0;
      data.rounds.forEach((r) => { s += r.p1_payoff; cum.push(s); });
      el("rps-score-chart").style.display = "";
      Plotly.newPlot("rps-score-chart", [{
        y: cum, mode: "lines", name: "P1 cumulative payoff",
      }], {
        title: "Player 1 cumulative payoff over rounds",
        xaxis: { title: "Round" }, yaxis: { title: "Cumulative payoff" },
        margin: { t: 40 },
      }, { displayModeBar: false });
      const f = data.summary.empirical_frequencies;
      setStatus(el("rps-status"),
        `Done. Empirical frequencies — P1: [${f[0].map((x) => x.toFixed(2))}], ` +
        `P2: [${f[1].map((x) => x.toFixed(2))}]`);
    } catch (err) {
      setStatus(el("rps-status"), err.message, true);
    } finally {
      el("rps-autorun").disabled = false;
    }
  });
})();
