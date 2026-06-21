// Leduc Poker play tab. Static (GitHub Pages) builds always show a
// "watch a recorded hand" walkthrough (see web/templates/leduc.html for why
// there's no static-mode live engine). The live FastAPI/Render app shows a
// real human-vs-bot match instead, mirroring kuhn.js's pattern.
(() => {
  const el = (id) => document.getElementById(id);
  const tabsRoot = document.getElementById("leduc-tabs");
  if (tabsRoot) {
    initTabs(tabsRoot, (paneId) => {
      if (paneId === "pane-ltrain" && window.leducTrainPlaceholders) window.leducTrainPlaceholders();
    });
  }
  if (!el("l-walk-start") && !el("l-start")) return;

  const RANK = { Jack: "J", Queen: "Q", King: "K" };

  function setCard(cardEl, rankEl, cardName, reveal) {
    if (reveal && cardName) {
      rankEl.textContent = RANK[cardName] || "?";
      cardEl.classList.add("flipped");
    } else {
      cardEl.classList.remove("flipped");
    }
  }

  function betLog(container, actions) {
    container.innerHTML = "";
    (actions || []).forEach((a) => {
      const chip = document.createElement("span");
      chip.className = "bchip" + (a.player === 0 ? " you" : "");
      chip.textContent = `P${a.player + 1}: ${a.label}`;
      container.appendChild(chip);
    });
  }

  function appendHandLog(hand) {
    const tbody = el("l-log").querySelector("tbody");
    const tr = document.createElement("tr");
    const cards = Object.entries(hand.cards).map(([k, v]) => `${k.toUpperCase()}: ${v}`).join(", ");
    tr.innerHTML = `<td>${hand.hand}</td><td>${hand.public_card || "—"}</td>` +
      `<td>${hand.showdown ? "showdown" : "fold"}</td><td>${cards}</td>` +
      `<td>${hand.payoffs[0]}</td>`;
    tbody.prepend(tr);
  }

  /* ==================== static-mode walkthrough ==================== */
  if (el("l-walk-start")) {
    let hands = [];
    let seatLabels = ["Player 1", "Player 2"];
    let idx = -1;
    let totals = [0, 0];

    function renderHand(i) {
      const hand = hands[i];
      el("l-game").style.display = "";
      el("l-total1").textContent = totals[0].toFixed(0);
      el("l-total2").textContent = totals[1].toFixed(0);
      el("l-handno").textContent = `${i + 1} / ${hands.length}`;

      setCard(el("l-your-card"), el("l-your-rank"), hand.cards.p1, true);
      setCard(el("l-opp-card"), el("l-opp-rank"), hand.cards.p2, hand.showdown);
      setCard(el("l-public-card"), el("l-public-rank"), hand.public_card, !!hand.public_card);

      el("l-pot").textContent = hand.pot;
      betLog(el("l-round1-log"), hand.round1_actions);
      betLog(el("l-round2-log"), hand.round2_actions);
      el("l-actions").innerHTML = "";

      const banner = el("l-banner");
      const p1Win = hand.payoffs[0] > 0;
      banner.className = `hand-banner ${p1Win ? "win" : hand.payoffs[0] < 0 ? "lose" : ""}`;
      banner.innerHTML = hand.payoffs[0] === 0 ? "DRAW" :
        `${p1Win ? "P1 WINS" : "P2 WINS"} <span class="delta">${hand.payoffs[0] > 0 ? "+" : ""}${hand.payoffs[0]}</span>` +
        `${hand.showdown ? "" : " (fold — no reveal)"}`;
    }

    function goTo(i) {
      idx = Math.max(0, Math.min(i, hands.length - 1));
      totals = [0, 0];
      el("l-log").querySelector("tbody").innerHTML = "";
      for (let k = 0; k <= idx; k++) {
        totals[0] += hands[k].payoffs[0];
        totals[1] += hands[k].payoffs[1];
        appendHandLog(hands[k]);
      }
      renderHand(idx);
      el("l-walk-step-label").textContent = `Hand ${idx + 1} / ${hands.length}`;
      el("l-walk-prev").disabled = idx <= 0;
      el("l-walk-next").disabled = idx >= hands.length - 1;
    }

    el("l-walk-prev").addEventListener("click", () => goTo(idx - 1));
    el("l-walk-next").addEventListener("click", () => goTo(idx + 1));

    el("l-walk-start").addEventListener("click", async () => {
      try {
        setStatus(el("l-status"), "Loading recorded match…");
        el("l-walk-start").disabled = true;
        const id = el("l-walk-pick").value;
        const data = await getJSON(`${window.SITE_BASE || ""}/static/data/walkthroughs/leduc_${id}.json`);
        hands = data.hands;
        seatLabels = data.seat_labels;
        el("l-who1").textContent = `P1 — ${seatLabels[0]}`;
        el("l-who2").textContent = `P2 — ${seatLabels[1]}`;
        setStatus(el("l-status"), "Loaded — step through hands with Prev/Next.");
        goTo(0);
      } catch (err) {
        setStatus(el("l-status"), err.message, true);
      } finally {
        el("l-walk-start").disabled = false;
      }
    });
  }

  /* ==================== live mode (FastAPI/Render) ==================== */
  if (el("l-start")) {
    let matchId = null;
    let isAuto = false;
    let lastLoggedHand = 0;
    let humanSeat = null;
    let bankroll = [];
    let revealTimer = null;

    function labelOf(sel) { return sel.options[sel.selectedIndex].text; }

    function updateBankrollChart() {
      if (bankroll.length < 2) return;
      el("l-bankroll-chart").style.display = "";
      Plotly.react("l-bankroll-chart", [{
        y: bankroll, mode: "lines+markers", name: "your chips",
        line: { color: "#fbbf24", width: 2 }, marker: { size: 5 },
      }], mergeAxes(darkLayout({ title: { text: "Your bankroll over hands" }, height: 300 }),
        { title: { text: "Hand" } }, { title: { text: "Cumulative chips" } }),
        PLOT_CONFIG);
    }

    function showBanner(lastHand) {
      const banner = el("l-banner");
      const myPayoff = lastHand.payoffs[humanSeat];
      const win = myPayoff > 0;
      banner.className = `hand-banner ${win ? "win" : "lose"}`;
      banner.innerHTML = `${win ? "YOU WIN" : "YOU LOSE"} ` +
        `<span class="delta">${myPayoff > 0 ? "+" : ""}${myPayoff}</span>` +
        `${lastHand.showdown ? "" : " (fold — no reveal)"}`;
    }

    function actionButtons(view) {
      const actions = el("l-actions");
      actions.innerHTML = "";
      if (!view.to_act) {
        const span = document.createElement("span");
        span.className = "status";
        span.textContent = "waiting for opponent…";
        actions.appendChild(span);
        return;
      }
      view.legal_actions.forEach(({ action, label }) => {
        const b = document.createElement("button");
        if (action === 2) { b.className = "pact aggr"; b.textContent = label.toUpperCase(); }
        else if (action === 0) { b.className = "pact passv"; b.textContent = "FOLD"; }
        else { b.className = "pact passv"; b.textContent = label.toUpperCase(); }
        b.addEventListener("click", () => act(action));
        actions.appendChild(b);
      });
    }

    function renderTableState(view) {
      if (view.finished || view.to_act === undefined) return;
      el("l-table").style.display = "";
      setCard(el("l-your-card"), el("l-your-rank"), view.your_card, true);
      setCard(el("l-public-card"), el("l-public-rank"), view.public_card, !!view.public_card);
      el("l-pot").textContent = view.pot;
      betLog(el("l-round1-log"), view.round1_log);
      betLog(el("l-round2-log"), view.round2_log);
      actionButtons(view);
    }

    function render(view) {
      el("l-game").style.display = "";
      el("l-total1").textContent = view.totals[0].toFixed(0);
      el("l-total2").textContent = view.totals[1].toFixed(0);
      el("l-handno").textContent = `${view.hands_played} / ${view.hands_total}`;

      const newHandFinished = view.last_hand && view.last_hand.hand > lastLoggedHand;

      if (newHandFinished) {
        const lh = view.last_hand;
        appendHandLog(lh);
        lastLoggedHand = lh.hand;
        bankroll.push((bankroll[bankroll.length - 1] || 0) + lh.payoffs[humanSeat]);
        showBanner(lh);
        updateBankrollChart();
        const oppKey = `p${(1 - humanSeat) + 1}`;
        setCard(el("l-opp-card"), el("l-opp-rank"), lh.cards[oppKey], lh.showdown);
        el("l-actions").innerHTML = "";
        if (view.finished) {
          setStatus(el("l-status"),
            `Match finished. Your net: ${view.totals[humanSeat]} chips over ${view.hands_played} hands ` +
            `(${(view.totals[humanSeat] / view.hands_played).toFixed(3)} chips/hand).`);
          return;
        }
        clearTimeout(revealTimer);
        revealTimer = setTimeout(() => {
          el("l-banner").className = "hand-banner";
          el("l-banner").textContent = "";
          setCard(el("l-opp-card"), el("l-opp-rank"), null, false);
          renderTableState(view);
        }, 1500);
        return;
      }
      renderTableState(view);
    }

    async function act(action) {
      try {
        const view = await postJSON(`/api/leduc/${matchId}/act`, { action });
        render(view);
      } catch (err) {
        setStatus(el("l-status"), err.message, true);
      }
    }

    el("l-start").addEventListener("click", async () => {
      const p1 = el("l-p1").value, p2 = el("l-p2").value;
      isAuto = p1 !== "human" && p2 !== "human";
      try {
        setStatus(el("l-status"),
          "Starting… (training the bot policy if this is its first use — may take a little while)");
        el("l-start").disabled = true;
        const view = await postJSON("/api/leduc/new", {
          p1, p2, hands: +el("l-hands").value, seed: Math.floor(Math.random() * 1e6),
        });
        matchId = view.match_id;
        lastLoggedHand = 0;
        bankroll = [0];
        humanSeat = p1 === "human" ? 0 : p2 === "human" ? 1 : null;
        el("l-log").querySelector("tbody").innerHTML = "";
        el("l-auto-result").style.display = "none";
        el("l-bankroll-chart").style.display = "none";
        el("l-banner").className = "hand-banner";
        el("l-banner").textContent = "";
        setCard(el("l-opp-card"), el("l-opp-rank"), null, false);
        el("l-who1").textContent = `P1 — ${labelOf(el("l-p1"))}`;
        el("l-who2").textContent = `P2 — ${labelOf(el("l-p2"))}`;
        if (isAuto) {
          el("l-table").style.display = "none";
          setStatus(el("l-status"), `Simulating ${+el("l-hands").value} hands…`);
          const res = await postJSON(`/api/leduc/${matchId}/auto`);
          el("l-game").style.display = "";
          el("l-total1").textContent = res.totals[0].toFixed(0);
          el("l-total2").textContent = res.totals[1].toFixed(0);
          el("l-handno").textContent = `${res.hands} / ${res.hands}`;
          el("l-auto-result").style.display = "";
          el("l-auto-stats").innerHTML =
            `<div class="stat"><div class="v">${res.p1_mean_payoff.toFixed(4)}</div><div class="k">P1 mean chips/hand</div></div>` +
            `<div class="stat"><div class="v">[${res.ci_low.toFixed(4)}, ${res.ci_high.toFixed(4)}]</div><div class="k">95% CI</div></div>` +
            `<div class="stat"><div class="v">${(res.p1_win_rate * 100).toFixed(1)}%</div><div class="k">P1 win rate</div></div>` +
            `<div class="stat"><div class="v">${res.hands.toLocaleString()}</div><div class="k">hands</div></div>`;
          setStatus(el("l-status"), "Done.");
        } else {
          setStatus(el("l-status"), "Match started — good luck.");
          render(view);
        }
      } catch (err) {
        setStatus(el("l-status"), err.message, true);
      } finally {
        el("l-start").disabled = false;
      }
    });
  }
})();
