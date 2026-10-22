// Visual report (SPEC §8). Report data comes from an LLM: it is untrusted, so every
// piece of it is set with textContent and never innerHTML.
(() => {
  "use strict";

  const DISCLAIMER = "Indicative, based on a short self-reported interview. Not a hiring assessment.";
  const DIMENSION_NAMES = {
    breadth: "Tool and model breadth",
    prompting: "Prompting and context",
    verification: "Critical evaluation",
    building: "Building with AI APIs",
    voice_audio: "Voice and audio AI",
    responsible: "Responsible use",
    customer_value: "Turning AI into value",
  };
  const SCORE_LABELS = ["", "Unaware", "Exploring", "Practising", "Building", "Leading"];
  const IMPORTANCE = { 3: "High", 2: "Medium", 1: "Low" };

  let chart = null;
  let lastReport = null;
  let lastRole = null;

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function append(parent, ...children) {
    for (const child of children) if (child) parent.append(child);
    return parent;
  }

  function dimName(id) {
    return DIMENSION_NAMES[id] || String(id);
  }

  function seconds(ms) {
    return `${(ms / 1000).toFixed(1)}s`;
  }

  function mean(values) {
    return values.reduce((a, b) => a + b, 0) / values.length;
  }

  async function fetchRole() {
    try {
      const res = await fetch("/api/role");
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }

  function list(items, emptyText) {
    const ul = el("ul", "report-list");
    if (!items.length) {
      ul.append(el("li", "muted", emptyText));
      return ul;
    }
    for (const item of items) ul.append(item);
    return ul;
  }

  // ---- header -------------------------------------------------------------------

  function ring(percent) {
    const pct = Math.max(0, Math.min(100, Number(percent) || 0));
    const wrap = el("div", "fit-ring");
    wrap.style.setProperty("--pct", pct);
    wrap.setAttribute("role", "img");
    wrap.setAttribute("aria-label", `${pct} percent fit`);
    const inner = el("div", "fit-ring-inner");
    inner.append(el("span", "fit-number", pct), el("span", "fit-percent", "%"));
    wrap.append(inner);
    return wrap;
  }

  function header(report) {
    const fit = report.role_fit;
    const card = el("div", "card report-header");
    const text = el("div", "report-header-text");
    text.append(
      el("h2", "report-title", `Fit for ${fit.role_title}`),
      el("p", "fit-band", fit.band),
      el("p", "report-summary", report.assessment.summary),
    );
    const level = el("p", "level-line");
    level.append(
      el("span", "chip", `AI literacy: ${report.level}`),
      el("span", "muted", ` mean ${Number(report.overall_score).toFixed(1)} / 5`),
    );
    text.append(level, el("p", "disclaimer", DISCLAIMER));
    card.append(ring(fit.fit_percent), text);
    return card;
  }

  // ---- meets / gaps -------------------------------------------------------------

  function meetsAndGaps(report, role) {
    const fit = report.role_fit;
    const byId = new Map(fit.dimensions.map((d) => [d.dimension_id, d]));
    const whyById = new Map(((role && role.requirements) || []).map((r) => [r.dimension_id, r.why]));

    const meetItems = fit.meets.map((id) => {
      const d = byId.get(id);
      const li = el("li");
      li.append(el("strong", "", dimName(id)));
      if (d) li.append(el("span", "muted", ` ${d.score} / ${d.target}`));
      return li;
    });
    const gapItems = fit.gaps.map((id) => {
      const d = byId.get(id);
      const li = el("li");
      li.append(el("strong", "", dimName(id)));
      if (d) li.append(el("span", "gap-arrow", ` ${d.score} → ${d.target}`));
      const why = whyById.get(id);
      if (why) li.append(el("p", "muted small", why));
      return li;
    });

    const grid = el("div", "report-two");
    const meets = el("section", "card");
    append(
      meets,
      el("h3", "", "Where you meet the role"),
      list(meetItems, "No dimension is at target yet."),
    );
    const gaps = el("section", "card");
    append(gaps, el("h3", "", "Gaps to close"), list(gapItems, "No gaps: you meet every target."));
    grid.append(meets, gaps);
    return grid;
  }

  // ---- radar chart --------------------------------------------------------------

  function cssColour(name, alpha) {
    const raw = getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#888888";
    if (alpha === undefined) return raw;
    const ctx = document.createElement("canvas").getContext("2d");
    ctx.fillStyle = raw;
    const hex = ctx.fillStyle; // normalised to #rrggbb
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
  }

  function radarCard() {
    const card = el("section", "card radar-card");
    card.append(el("h3", "", "You against the role"));
    const box = el("div", "radar-box");
    const canvas = el("canvas");
    canvas.id = "radar-canvas";
    canvas.setAttribute("role", "img");
    canvas.setAttribute("aria-label", "Radar chart comparing your scores with the role targets");
    box.append(canvas);
    card.append(box, el("p", "muted small radar-fallback"));
    return card;
  }

  // Chart.js draws an array label as several lines; wrapping keeps labels on-screen.
  function wrapLabel(text, max) {
    const lines = [];
    let line = "";
    for (const word of text.split(" ")) {
      if (line && (line + " " + word).length > max) {
        lines.push(line);
        line = word;
      } else {
        line = line ? `${line} ${word}` : word;
      }
    }
    if (line) lines.push(line);
    return lines;
  }

  function drawRadar(report) {
    const canvas = document.getElementById("radar-canvas");
    if (!canvas) return;
    const fallback = canvas.closest(".radar-card").querySelector(".radar-fallback");
    if (chart) {
      chart.destroy();
      chart = null;
    }
    if (typeof window.Chart !== "function") {
      canvas.hidden = true;
      fallback.textContent = "The chart could not load (the Chart.js library is unavailable). The scores are listed below.";
      return;
    }
    canvas.hidden = false;
    fallback.textContent = "";
    const dims = report.role_fit.dimensions;
    const text = cssColour("--text");
    const muted = cssColour("--muted");
    const grid = cssColour("--border");
    chart = new window.Chart(canvas, {
      type: "radar",
      data: {
        labels: dims.map((d) => wrapLabel(dimName(d.dimension_id), 14)),
        datasets: [
          {
            label: "You",
            data: dims.map((d) => d.score),
            borderColor: cssColour("--accent"),
            backgroundColor: cssColour("--accent", 0.25),
            pointBackgroundColor: cssColour("--accent"),
            borderWidth: 2,
            fill: true,
          },
          {
            label: "Role target",
            data: dims.map((d) => d.target),
            borderColor: cssColour("--warn"),
            backgroundColor: "transparent",
            pointBackgroundColor: cssColour("--warn"),
            borderDash: [6, 4],
            borderWidth: 2,
            fill: false,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: {
            min: 1,
            max: 5,
            ticks: { stepSize: 1, color: muted, backdropColor: "transparent" },
            grid: { color: grid },
            angleLines: { color: grid },
            pointLabels: { color: text, font: { size: 11 }, padding: 4 },
          },
        },
        plugins: { legend: { labels: { color: text } } },
      },
    });
  }

  // ---- dimension cards ----------------------------------------------------------

  function dimensionCards(report) {
    const byId = new Map(report.assessment.dimensions.map((d) => [d.dimension_id, d]));
    const wrap = el("section", "report-section");
    wrap.append(el("h3", "", "Dimension by dimension"));
    for (const fit of report.role_fit.dimensions) {
      const d = byId.get(fit.dimension_id) || { score: fit.score, evidence_quote: "", rationale: "" };
      const card = el("article", "card dim-card");
      const head = el("div", "dim-head");
      head.append(
        el("h4", "", dimName(fit.dimension_id)),
        el("span", "chip", `${IMPORTANCE[fit.weight] || "Medium"} importance for this role`),
      );
      const score = el("p", "dim-score");
      score.append(
        el("strong", "", `${fit.score} / 5 · target ${fit.target}`),
        el("span", "muted", ` ${SCORE_LABELS[fit.score] || ""}`),
      );
      const quote = (d.evidence_quote || "").trim();
      card.append(
        head,
        score,
        quote ? el("blockquote", "quote", `“${quote}”`) : el("p", "muted no-evidence", "No evidence given"),
        el("p", "", d.rationale),
      );
      wrap.append(card);
    }
    return wrap;
  }

  // ---- strengths / narrative gaps ----------------------------------------------

  function strengthsAndGaps(report) {
    const a = report.assessment;
    const grid = el("div", "report-two");
    const s = el("section", "card");
    append(
      s,
      el("h3", "", "Strengths"),
      list(a.strengths.map((t) => el("li", "", t)), "None listed."),
    );
    const g = el("section", "card");
    append(g, el("h3", "", "Gaps"), list(a.gaps.map((t) => el("li", "", t)), "None listed."));
    grid.append(s, g);
    return grid;
  }

  // ---- development plan ---------------------------------------------------------

  function plan(report) {
    const wrap = el("section", "report-section");
    wrap.append(el("h3", "", "Your development plan for this role"));
    for (const rec of report.assessment.recommendations) {
      const card = el("article", "card rec-card");
      const head = el("div", "dim-head");
      head.append(el("h4", "", rec.title), el("span", "chip", `${rec.effort} effort`));
      const first = el("p");
      first.append(el("strong", "", "First step: "), document.createTextNode(rec.first_step));
      card.append(
        head,
        el("p", "muted small", `Builds: ${dimName(rec.dimension_id)}`),
        el("p", "", rec.why),
        first,
      );
      wrap.append(card);
    }
    return wrap;
  }

  // ---- footer and actions -------------------------------------------------------

  function footer(report) {
    const m = report.metrics || {};
    const parts = [`Assessed by ${report.provider} (${report.model})`];
    if (m.stt_ms && m.stt_ms.length) parts.push(`speech-to-text avg ${seconds(mean(m.stt_ms))}`);
    if (m.tts_ms && m.tts_ms.length) parts.push(`text-to-speech avg ${seconds(mean(m.tts_ms))}`);
    if (typeof m.llm_assess_ms === "number") parts.push(`assessment ${seconds(m.llm_assess_ms)}`);
    if (typeof m.llm_followup_ms === "number") parts.push(`follow-up ${seconds(m.llm_followup_ms)}`);
    if (m.cached_response) parts.push("same answers as an earlier run: reused, no new model call");
    if (report.provider === "ollama") parts.push("est. cost $0.00 (local)");
    else if (typeof m.est_cost_usd === "number") {
      // Haiku interviews cost fractions of a cent, so small amounts keep more decimals.
      const cost = m.est_cost_usd;
      parts.push(`est. cost $${cost >= 0.01 || cost === 0 ? cost.toFixed(2) : cost.toFixed(4)}`);
    }
    if (m.cache_read_tokens) parts.push(`${m.cache_read_tokens} prompt tokens from cache`);
    const when = new Date(report.generated_at);
    if (!Number.isNaN(when.getTime())) parts.push(`generated ${when.toLocaleString("en-GB")}`);
    return el("footer", "report-footer muted small", parts.join(" · "));
  }

  function download(report) {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ai-role-fit-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.append(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function actions(report) {
    const row = el("div", "actions report-actions");
    const dl = el("button", "primary", "Download JSON");
    dl.type = "button";
    dl.addEventListener("click", () => download(report));
    const again = el("button", "", "Start again");
    again.type = "button";
    again.addEventListener("click", () => window.location.reload());
    row.append(dl, again);
    return row;
  }

  // ---- entry point --------------------------------------------------------------

  async function renderReport(report) {
    lastReport = report;
    lastRole = await fetchRole();
    for (const id of ["start", "interview"]) document.getElementById(id).hidden = true;
    const content = document.getElementById("report-content");
    content.replaceChildren(
      header(report),
      meetsAndGaps(report, lastRole),
      radarCard(),
      dimensionCards(report),
      strengthsAndGaps(report),
      plan(report),
      footer(report),
      actions(report),
    );
    document.getElementById("report").hidden = false;
    drawRadar(report);
    window.scrollTo(0, 0);
  }

  window.renderReport = renderReport;

  // Redraw the chart when the theme changes so its colours follow the CSS variables.
  window
    .matchMedia("(prefers-color-scheme: dark)")
    .addEventListener("change", () => lastReport && drawRadar(lastReport));
})();
