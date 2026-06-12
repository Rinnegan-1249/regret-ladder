// Animated constellation background for the landing hero.
// Dependency-free canvas: drifting nodes, distance-faded links, gentle
// mouse parallax. Pauses when the tab is hidden.
(() => {
  const canvas = document.getElementById("hero-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const hero = canvas.parentElement;

  let W = 0, H = 0, dpr = 1;
  let nodes = [];
  const mouse = { x: -1e9, y: -1e9 };
  const N = 80;
  const LINK_DIST = 150;

  const COLORS = ["rgba(52,227,164,", "rgba(56,189,248,"]; // mint, cyan

  function resize() {
    dpr = window.devicePixelRatio || 1;
    W = hero.clientWidth;
    H = hero.clientHeight;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    canvas.style.width = `${W}px`;
    canvas.style.height = `${H}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function init() {
    resize();
    nodes = Array.from({ length: N }, () => ({
      x: Math.random() * W,
      y: Math.random() * H,
      vx: (Math.random() - 0.5) * 0.35,
      vy: (Math.random() - 0.5) * 0.35,
      r: 1.2 + Math.random() * 1.8,
      c: COLORS[Math.random() < 0.7 ? 0 : 1],
    }));
  }

  function step() {
    ctx.clearRect(0, 0, W, H);

    for (const n of nodes) {
      // gentle mouse repulsion
      const dx = n.x - mouse.x, dy = n.y - mouse.y;
      const md2 = dx * dx + dy * dy;
      if (md2 < 120 * 120) {
        const f = 0.6 / Math.max(Math.sqrt(md2), 20);
        n.vx += dx * f * 0.02;
        n.vy += dy * f * 0.02;
      }
      // speed cap + drift
      n.vx = Math.max(-0.6, Math.min(0.6, n.vx));
      n.vy = Math.max(-0.6, Math.min(0.6, n.vy));
      n.x += n.vx;
      n.y += n.vy;
      if (n.x < -10) n.x = W + 10; else if (n.x > W + 10) n.x = -10;
      if (n.y < -10) n.y = H + 10; else if (n.y > H + 10) n.y = -10;
    }

    // links
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i], b = nodes[j];
        const dx = a.x - b.x, dy = a.y - b.y;
        const d2 = dx * dx + dy * dy;
        if (d2 < LINK_DIST * LINK_DIST) {
          const alpha = 0.14 * (1 - Math.sqrt(d2) / LINK_DIST);
          ctx.strokeStyle = `rgba(120,200,180,${alpha.toFixed(3)})`;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }
    }

    // nodes
    for (const n of nodes) {
      ctx.fillStyle = `${n.c}0.55)`;
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  let raf = null;
  function loop() {
    step();
    raf = requestAnimationFrame(loop);
  }

  hero.addEventListener("mousemove", (e) => {
    const rect = canvas.getBoundingClientRect();
    mouse.x = e.clientX - rect.left;
    mouse.y = e.clientY - rect.top;
  });
  hero.addEventListener("mouseleave", () => { mouse.x = -1e9; mouse.y = -1e9; });
  window.addEventListener("resize", resize);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) { cancelAnimationFrame(raf); raf = null; }
    else if (!raf) loop();
  });

  init();
  loop();
})();
