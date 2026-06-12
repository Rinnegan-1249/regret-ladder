// RPS play tab logic — gamified duel with hidden simultaneous reveal.
(() => {
  const el = (id) => document.getElementById(id);
  const tabsRoot = document.getElementById("rps-tabs");
  if (tabsRoot) {
    initTabs(tabsRoot, (paneId) => {
      if (paneId === "pane-train" && window.rpsTrainPlaceholders) window.rpsTrainPlaceholders();
    });
  }
  if (!el("rps-start")) return;

  let match = null; // {id, seats, finished}
  let streak = 0;   // P1 perspective

  const HANDS = ["✊", "✋", "✌️"]; // rock, paper, scissors emoji
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

  function bump(scoreEl, good) {
    scoreEl.classList.remove("bump", "bump-bad");
    void scoreEl.offsetWidth; // restart animation
    scoreEl.classList.add(good ? "bump" : "bump-bad");
  }

  function updateScoreboard(summary) {
    el("rps-score1").textContent = summary.scores[0].toFixed(0);
    el("rps-score2").textContent = summary.scores[1].toFixed(0);
    el("rps-roundno").textContent = `${summary.rounds_played} / ${summary.rounds_total}`;
  }

  function updateStreak(p1Payoff) {
    if (p1Payoff > 0) streak = streak > 0 ? streak + 1 : 1;
    else if (p1Payoff < 0) streak = streak < 0 ? streak - 1 : -1;
    else streak = 0;
    el("rps-streak").textContent =
      streak > 1 ? `P1 ×${streak} \u{1F525}` :
      streak < -1 ? `P2 ×${-streak} \u{1F525}` : "—";
  }

  function appendLog(row) {
    const tbody = el("rps-log").querySelector("tbody");
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${row.round}</td><td>${HANDS[row.p1_action]} ${ACTION_NAMES[row.p1_action]}</td>` +
      `<td>${HANDS[row.p2_action]} ${ACTION_NAMES[row.p2_action]}</td><td>${row.p1_payoff}</td>` +
      `<td>${row.scores[0]} : ${row.scores[1]}</td>`;
    tbody.prepend(tr);
  }

  function appendHistoryDot(p1Payoff) {
    const dot = document.createElement("div");
    dot.className = `dot ${p1Payoff > 0 ? "w" : p1Payoff < 0 ? "l" : "d"}`;
    dot.title = p1Payoff > 0 ? "P1 win" : p1Payoff < 0 ? "P2 win" : "draw";
    el("rps-history").appendChild(dot);
  }

  function showAdaptive(row) {
    const key = match.seats[0] === "rm_adaptive" ? "p1_adaptive_strategy"
      : match.seats[1] === "rm_adaptive" ? "p2_adaptive_strategy" : null;
    if (!key || !row[key]) return;
    el("rps-adaptive-view").style.display = "";
    const bars = el("rps-adaptive-bars");
    if (!bars.children.length) {
      ACTION_NAMES.forEach((name, i) => {
        const rowDiv = document.createElement("div");
        rowDiv.className = "row";
        rowDiv.innerHTML = `<div class="lbl">${HANDS[i]} ${name}</div>` +
          `<div class="track"><div class="fill" id="rps-fill-${i}" style="width:33%"></div></div>` +
          `<div class="pct" id="rps-pct-${i}">33%</div>`;
        bars.appendChild(rowDiv);
      });
    }
    row[key].forEach((p, i) => {
      el(`rps-fill-${i}`).style.width = `${(p * 100).toFixed(1)}%`;
      el(`rps-pct-${i}`).textContent = `${(p * 100).toFixed(1)}%`;
    });
  }

  // Duel animation: shake fists, then reveal both hands and the verdict.
  function playReveal(row, humanSeat) {
    const duel = el("rps-duel");
    const verdict = el("rps-verdict");
    el("rps-fist1").textContent = "✊";
    el("rps-fist2").textContent = "✊";
    verdict.className = "verdict";
    verdict.textContent = "";
    duel.classList.remove("shaking");
    void duel.offsetWidth;
    duel.classList.add("shaking");
    setHandButtonsEnabled(false);
    setTimeout(() => {
      el("rps-fist1").textContent = HANDS[row.p1_action];
      el("rps-fist2").textContent = HANDS[row.p2_action];
      const u = row.p1_payoff;
      let cls = "draw", text = "DRAW";
      if (u !== 0) {
        const p1Wins = u > 0;
        if (humanSeat !== null) {
          const youWin = (humanSeat === 0) === p1Wins;
          cls = youWin ? "win" : "lose";
          text = youWin ? "YOU WIN" : "YOU LOSE";
        } else {
          cls = p1Wins ? "win" : "lose";
          text = p1Wins ? "P1 WINS" : "P2 WINS";
        }
        bump(el(p1Wins ? "rps-score1" : "rps-score2"), true);
      }
      verdict.className = `verdict ${cls}`;
      verdict.textContent = text;
      setHandButtonsEnabled(true);
      promptNext();
    }, 580);
  }

  function setHandButtonsEnabled(on) {
    el("rps-actions").querySelectorAll("button.hand").forEach((b) => { b.disabled = !on; });
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
        : `You are Player ${humans[0] + 1} — throw your hand`;
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
          el("rps-prompt").textContent = "Player 2's turn — throw your hand";
          return;
        }
        await playRound(pendingP1, action);
        pendingP1 = null;
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
    const humans = humanSeats();
    appendLog(data.round);
    appendHistoryDot(data.round.p1_payoff);
    showAdaptive(data.round);
    updateScoreboard(data.summary);
    updateStreak(data.round.p1_payoff);
    match.finished = data.summary.finished;
    setStatus(el("rps-status"), "");
    playReveal(data.round, humans.length === 1 ? humans[0] : null);
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
      streak = 0;
      el("rps-game").style.display = "";
      el("rps-log").querySelector("tbody").innerHTML = "";
      el("rps-history").innerHTML = "";
      el("rps-adaptive-bars").innerHTML = "";
      el("rps-autorun").style.display = "none";
      el("rps-actions").style.display = "none";
      el("rps-adaptive-view").style.display = "none";
      el("rps-score-chart").style.display = "none";
      el("rps-verdict").className = "verdict";
      el("rps-verdict").textContent = "";
      el("rps-fist1").textContent = "✊";
      el("rps-fist2").textContent = "✊";
      el("rps-streak").textContent = "—";
      el("rps-who1").textContent = `P1 — ${seatLabel(match.seats[0])}`;
      el("rps-who2").textContent = `P2 — ${seatLabel(match.seats[1])}`;
      el("rps-duel-who1").textContent = seatLabel(match.seats[0]);
      el("rps-duel-who2").textContent = seatLabel(match.seats[1]);
      updateScoreboard(summary);
      setStatus(el("rps-status"), "Match started.");
      pendingP1 = null;
      promptNext();
    } catch (err) {
      setStatus(el("rps-status"), err.message, true);
    }
  });

  el("rps-actions").querySelectorAll("button.hand").forEach((b) =>
    b.addEventListener("click", () => humanPick(+b.dataset.a)));

  el("rps-autorun").addEventListener("click", async () => {
    try {
      el("rps-autorun").disabled = true;
      const data = await postJSON(`/api/rps/${match.id}/auto`);
      data.rounds.forEach((r) => { appendLog(r); appendHistoryDot(r.p1_payoff); });
      if (data.rounds.length) {
        showAdaptive(data.rounds[data.rounds.length - 1]);
        const last = data.rounds[data.rounds.length - 1];
        el("rps-fist1").textContent = HANDS[last.p1_action];
        el("rps-fist2").textContent = HANDS[last.p2_action];
      }
      updateScoreboard(data.summary);
      match.finished = true;
      const cum = [];
      let s = 0;
      data.rounds.forEach((r) => { s += r.p1_payoff; cum.push(s); });
      el("rps-score-chart").style.display = "";
      Plotly.newPlot("rps-score-chart", [{
        y: cum, mode: "lines", name: "P1 cumulative payoff",
        line: { color: "#34e3a4", width: 2 },
      }], mergeAxes(darkLayout({ title: { text: "Player 1 cumulative payoff over rounds" }, height: 320 }),
        { title: { text: "Round" } }, { title: { text: "Cumulative payoff" } }),
        PLOT_CONFIG);
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
