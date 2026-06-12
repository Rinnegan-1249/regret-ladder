// Kuhn Poker play tab logic.
(() => {
  const tabsRoot = document.getElementById("kuhn-tabs");
  if (tabsRoot) initTabs(tabsRoot);

  const el = (id) => document.getElementById(id);
  if (!el("k-start")) return;

  let matchId = null;
  let isAuto = false;

  function labelOf(sel) {
    return sel.options[sel.selectedIndex].text;
  }

  function appendHandLog(hand) {
    if (!hand) return;
    const tbody = el("k-log").querySelector("tbody");
    const tr = document.createElement("tr");
    const cards = Object.entries(hand.cards).map(([k, v]) => `${k.toUpperCase()}: ${v}`).join(", ");
    tr.innerHTML = `<td>${hand.hand}</td><td><code>${hand.betting}</code></td>` +
      `<td>${hand.showdown ? "showdown" : "fold"}</td><td>${cards}</td>` +
      `<td>${hand.payoffs[0]}</td>`;
    tbody.prepend(tr);
  }

  let lastLoggedHand = 0;

  function render(view) {
    el("k-game").style.display = "";
    el("k-total1").textContent = view.totals[0].toFixed(0);
    el("k-total2").textContent = view.totals[1].toFixed(0);
    el("k-handno").textContent = `${view.hands_played} / ${view.hands_total}`;

    if (view.last_hand && view.last_hand.hand > lastLoggedHand) {
      appendHandLog(view.last_hand);
      lastLoggedHand = view.last_hand.hand;
      const lh = view.last_hand;
      el("k-result").style.display = "";
      el("k-result").innerHTML =
        `Hand ${lh.hand}: betting <code>${lh.betting}</code> — ` +
        (lh.showdown ? "showdown" : "fold") +
        `, P1 ${lh.payoffs[0] > 0 ? "wins" : "loses"} ${Math.abs(lh.payoffs[0])}` +
        (lh.showdown ? ` (${Object.entries(lh.cards).map(([k, v]) => `${k.toUpperCase()}=${v}`).join(", ")})` : "");
    }

    if (view.finished) {
      el("k-table").style.display = "none";
      setStatus(el("k-status"),
        `Match finished. Player 1 net: ${view.totals[0]} chips over ${view.hands_played} hands ` +
        `(${(view.totals[0] / view.hands_played).toFixed(3)} chips/hand).`);
      return;
    }

    if (view.to_act !== undefined) {
      el("k-table").style.display = "";
      el("k-card").textContent = view.your_card;
      el("k-seat").textContent = view.your_seat;
      el("k-betting").textContent = view.betting || "(you open)";
      const actions = el("k-actions");
      actions.innerHTML = "";
      if (view.to_act) {
        view.legal_actions.forEach(({ action, label }) => {
          const b = document.createElement("button");
          b.className = "action";
          b.textContent = label;
          b.addEventListener("click", () => act(action));
          actions.appendChild(b);
        });
      }
    }
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
      el("k-log").querySelector("tbody").innerHTML = "";
      el("k-result").style.display = "none";
      el("k-auto-result").style.display = "none";
      el("k-who1").textContent = `P1 — ${labelOf(el("k-p1"))}`;
      el("k-who2").textContent = `P2 — ${labelOf(el("k-p2"))}`;
      if (isAuto) {
        setStatus(el("k-status"), `Simulating ${+el("k-hands").value} hands…`);
        const res = await postJSON(`/api/kuhn/${matchId}/auto`);
        el("k-game").style.display = "";
        el("k-table").style.display = "none";
        el("k-total1").textContent = res.totals[0].toFixed(0);
        el("k-total2").textContent = res.totals[1].toFixed(0);
        el("k-handno").textContent = `${res.hands} / ${res.hands}`;
        el("k-auto-result").style.display = "";
        el("k-auto-result").innerHTML =
          `<strong>Simulation result (${res.hands.toLocaleString()} hands):</strong> ` +
          `P1 mean payoff <strong>${res.p1_mean_payoff.toFixed(4)}</strong> chips/hand ` +
          `(95% CI [${res.ci_low.toFixed(4)}, ${res.ci_high.toFixed(4)}]), ` +
          `P1 win rate ${(res.p1_win_rate * 100).toFixed(1)}%.`;
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
