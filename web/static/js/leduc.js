// Leduc Poker "watch a recorded hand" widget — always a static walkthrough
// (no live engine; see web/templates/leduc.html for why). Steps hand-by-hand
// through a precomputed trajectory JSON built by scripts/build_web_static_data.py.
(() => {
  const el = (id) => document.getElementById(id);
  const tabsRoot = document.getElementById("leduc-tabs");
  if (tabsRoot) {
    initTabs(tabsRoot, (paneId) => {
      if (paneId === "pane-ltrain" && window.leducTrainPlaceholders) window.leducTrainPlaceholders();
    });
  }
  if (!el("l-walk-start")) return;

  const RANK = { Jack: "J", Queen: "Q", King: "K" };

  let hands = [];
  let seatLabels = ["Player 1", "Player 2"];
  let idx = -1;
  let totals = [0, 0];

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
    const cards = `P1: ${hand.cards.p1}, P2: ${hand.cards.p2}`;
    tr.innerHTML = `<td>${hand.hand}</td><td>${hand.public_card || "—"}</td>` +
      `<td>${hand.showdown ? "showdown" : "fold"}</td><td>${cards}</td>` +
      `<td>${hand.payoffs[0]}</td>`;
    tbody.prepend(tr);
  }

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
})();
