// Kuhn Poker play tab — poker-table UI with card flip reveals.
(() => {
  const el = (id) => document.getElementById(id);
  const tabsRoot = document.getElementById("kuhn-tabs");
  if (tabsRoot) {
    initTabs(tabsRoot, (paneId) => {
      if (paneId === "pane-ktrain" && window.kuhnTrainPlaceholders) window.kuhnTrainPlaceholders();
    });
  }
  if (!el("k-start")) return;

  let matchId = null;
  let isAuto = false;
  let lastLoggedHand = 0;
  let humanSeat = null;       // 0-based
  let bankroll = [];          // human cumulative chips per hand
  let revealTimer = null;

  const RANK = { Jack: "J", Queen: "Q", King: "K" };

  function labelOf(sel) { return sel.options[sel.selectedIndex].text; }

  function setYourCard(cardName) {
    const r = RANK[cardName] || "?";
    el("k-your-rank").textContent = r;
    el("k-your-idx-tl").textContent = r;
    el("k-your-idx-br").textContent = r;
  }

  function setOppCard(cardName, reveal) {
    const card = el("k-opp-card");
    if (reveal && cardName) {
      const r = RANK[cardName] || "?";
      el("k-opp-rank").textContent = r;
      el("k-opp-idx-tl").textContent = r;
      el("k-opp-idx-br").textContent = r;
      card.classList.add("flipped");
    } else {
      card.classList.remove("flipped");
    }
  }

  function potOf(betting) {
    return 2 + (betting.match(/b/g) || []).length;
  }

  function bettingChips(betting, yourSeat0) {
    const wrap = el("k-betchips");
    wrap.innerHTML = "";
    [...betting].forEach((c, i) => {
      const seat = i % 2; // P1 acts first
      const facingBet = i > 0 && betting[i - 1] === "b";
      const word = c === "b" ? (facingBet ? "call" : "bet") : (facingBet ? "fold" : "check");
      const chip = document.createElement("span");
      chip.className = "bchip" + (seat === yourSeat0 ? " you" : "");
      chip.textContent = `${seat === yourSeat0 ? "you" : "P" + (seat + 1)}: ${word}`;
      wrap.appendChild(chip);
    });
  }

  function actionButtons(view) {
    const actions = el("k-actions");
    actions.innerHTML = "";
    if (!view.to_act) {
      const span = document.createElement("span");
      span.className = "status";
      span.textContent = "waiting for opponent…";
      actions.appendChild(span);
      return;
    }
    const facingBet = (view.betting || "").endsWith("b");
    view.legal_actions.forEach(({ action }) => {
      const b = document.createElement("button");
      if (action === 1) {
        b.className = "pact aggr";
        b.textContent = facingBet ? "CALL +1" : "BET +1";
      } else {
        b.className = "pact passv";
        b.textContent = facingBet ? "FOLD" : "CHECK";
      }
      b.addEventListener("click", () => act(action));
      actions.appendChild(b);
    });
  }

  function appendHandLog(hand) {
    const tbody = el("k-log").querySelector("tbody");
    const tr = document.createElement("tr");
    const cards = Object.entries(hand.cards).map(([k, v]) => `${k.toUpperCase()}: ${v}`).join(", ");
    tr.innerHTML = `<td>${hand.hand}</td><td><code>${hand.betting}</code></td>` +
      `<td>${hand.showdown ? "showdown" : "fold"}</td><td>${cards}</td>` +
      `<td>${hand.payoffs[0]}</td>`;
    tbody.prepend(tr);
  }

  function updateBankrollChart() {
    if (bankroll.length < 2) return;
    el("k-bankroll-chart").style.display = "";
    Plotly.react("k-bankroll-chart", [{
      y: bankroll, mode: "lines+markers", name: "your chips",
      line: { color: "#fbbf24", width: 2 }, marker: { size: 5 },
    }], mergeAxes(darkLayout({ title: { text: "Your bankroll over hands" }, height: 300 }),
      { title: { text: "Hand" } }, { title: { text: "Cumulative chips" } }),
      PLOT_CONFIG);
  }

  function showBanner(lastHand) {
    const banner = el("k-banner");
    const myPayoff = lastHand.payoffs[humanSeat];
    const win = myPayoff > 0;
    banner.className = `hand-banner ${win ? "win" : "lose"}`;
    banner.innerHTML = `${win ? "YOU WIN" : "YOU LOSE"} ` +
      `<span class="delta">${myPayoff > 0 ? "+" : ""}${myPayoff}</span>` +
      `${lastHand.showdown ? "" : " (fold — no reveal)"}`;
  }

  function render(view) {
    el("k-game").style.display = "";
    el("k-total1").textContent = view.totals[0].toFixed(0);
    el("k-total2").textContent = view.totals[1].toFixed(0);
    el("k-handno").textContent = `${view.hands_played} / ${view.hands_total}`;

    const newHandFinished = view.last_hand && view.last_hand.hand > lastLoggedHand;

    if (newHandFinished) {
      const lh = view.last_hand;
      appendHandLog(lh);
      lastLoggedHand = lh.hand;
      bankroll.push((bankroll[bankroll.length - 1] || 0) + lh.payoffs[humanSeat]);
      showBanner(lh);
      updateBankrollChart();
      // Reveal the opponent card only at showdown.
      const oppKey = `p${(1 - humanSeat) + 1}`;
      setOppCard(lh.cards[oppKey], lh.showdown);
      el("k-actions").innerHTML = "";
      if (view.finished) {
        // Keep the final banner and reveal on screen.
        setStatus(el("k-status"),
          `Match finished. Your net: ${view.totals[humanSeat]} chips over ${view.hands_played} hands ` +
          `(${(view.totals[humanSeat] / view.hands_played).toFixed(3)} chips/hand).`);
        return;
      }
      // After the reveal pause, deal the next hand visually.
      clearTimeout(revealTimer);
      revealTimer = setTimeout(() => {
        el("k-banner").className = "hand-banner";
        el("k-banner").textContent = "";
        setOppCard(null, false);
        renderTableState(view);
      }, 1500);
      return;
    }
    renderTableState(view);
  }

  function renderTableState(view) {
    if (view.finished || view.to_act === undefined) return;
    el("k-table").style.display = "";
    setYourCard(view.your_card);
    el("k-seat").textContent = view.your_seat;
    el("k-pot").textContent = potOf(view.betting || "");
    bettingChips(view.betting || "", humanSeat);
    actionButtons(view);
  }

  async function act(action) {
    try {
      const view = await postJSON(`/api/kuhn/${matchId}/act`, { action });
      render(view);
    } catch (err) {
      setStatus(el("k-status"), err.message, true);
    }
  }

  el("k-start").addEventListener("click", async () => {
    const p1 = el("k-p1").value, p2 = el("k-p2").value;
    isAuto = p1 !== "human" && p2 !== "human";
    try {
      setStatus(el("k-status"),
        "Starting… (training the bot policy if this is its first use — up to ~30s)");
      el("k-start").disabled = true;
      const view = await postJSON("/api/kuhn/new", {
        p1, p2, hands: +el("k-hands").value, seed: Math.floor(Math.random() * 1e6),
      });
      matchId = view.match_id;
      lastLoggedHand = 0;
      bankroll = [0];
      humanSeat = p1 === "human" ? 0 : p2 === "human" ? 1 : null;
      el("k-log").querySelector("tbody").innerHTML = "";
      el("k-auto-result").style.display = "none";
      el("k-bankroll-chart").style.display = "none";
      el("k-banner").className = "hand-banner";
      el("k-banner").textContent = "";
      setOppCard(null, false);
      el("k-who1").textContent = `P1 — ${labelOf(el("k-p1"))}`;
      el("k-who2").textContent = `P2 — ${labelOf(el("k-p2"))}`;
      el("k-opp-label").textContent = humanSeat === null ? "Player 1"
        : (humanSeat === 0 ? labelOf(el("k-p2")) : labelOf(el("k-p1")));
      if (isAuto) {
        el("k-table").style.display = "none";
        setStatus(el("k-status"), `Simulating ${+el("k-hands").value} hands…`);
        const res = await postJSON(`/api/kuhn/${matchId}/auto`);
        el("k-game").style.display = "";
        el("k-total1").textContent = res.totals[0].toFixed(0);
        el("k-total2").textContent = res.totals[1].toFixed(0);
        el("k-handno").textContent = `${res.hands} / ${res.hands}`;
        el("k-auto-result").style.display = "";
        el("k-auto-stats").innerHTML =
          `<div class="stat"><div class="v">${res.p1_mean_payoff.toFixed(4)}</div><div class="k">P1 mean chips/hand</div></div>` +
          `<div class="stat"><div class="v">[${res.ci_low.toFixed(4)}, ${res.ci_high.toFixed(4)}]</div><div class="k">95% CI</div></div>` +
          `<div class="stat"><div class="v">${(res.p1_win_rate * 100).toFixed(1)}%</div><div class="k">P1 win rate</div></div>` +
          `<div class="stat"><div class="v">${res.hands.toLocaleString()}</div><div class="k">hands</div></div>`;
        setStatus(el("k-status"), "Done.");
      } else {
        setStatus(el("k-status"), "Match started — good luck.");
        render(view);
      }
    } catch (err) {
      setStatus(el("k-status"), err.message, true);
    } finally {
      el("k-start").disabled = false;
    }
  });
})();
