// Shared helpers: tabs, fetch wrappers, SSE consumption.

function initTabs(container, onActivate) {
  const tabs = container.querySelectorAll(".tabs button");
  const panes = container.querySelectorAll(".tabpane");
  tabs.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabs.forEach((b) => b.classList.remove("active"));
      panes.forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      const pane = container.querySelector(`#${btn.dataset.pane}`);
      pane.classList.add("active");
      // Plotly charts rendered while a pane was display:none have zero
      // width; resize them now that the pane is visible.
      if (window.Plotly) {
        pane.querySelectorAll(".chart, .chart-sm").forEach((div) => {
          if (div._fullLayout) Plotly.Plots.resize(div);
        });
      }
      if (onActivate) onActivate(btn.dataset.pane, pane);
    });
  });
}

async function postJSON(url, body) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.detail || `HTTP ${resp.status}`);
  return data;
}

async function getJSON(url) {
  const resp = await fetch(url);
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.detail || `HTTP ${resp.status}`);
  return data;
}

// Consume a Server-Sent-Events stream; calls onEvent(parsedJson) per event.
// Returns an object with .abort().
function consumeSSE(url, onEvent, onDone, onError) {
  const controller = new AbortController();
  fetch(url, { signal: controller.signal })
    .then(async (resp) => {
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let idx;
        while ((idx = buffer.indexOf("\n\n")) >= 0) {
          const chunk = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          const line = chunk.split("\n").find((l) => l.startsWith("data: "));
          if (line) onEvent(JSON.parse(line.slice(6)));
        }
      }
      if (onDone) onDone();
    })
    .catch((err) => {
      if (err.name !== "AbortError" && onError) onError(err);
    });
  return controller;
}

function setStatus(el, text, isError) {
  el.textContent = text;
  el.classList.toggle("error", !!isError);
}
