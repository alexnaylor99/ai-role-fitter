// Phase 1 placeholder: a minimal typed-only interview so the app works end to end.
// T4 replaces this file with the full voice interview (see docs/tasks/T4-interview-ui.md).
(() => {
  const $ = (id) => document.getElementById(id);
  let questions = [];
  let answers = [];
  let index = 0;
  let provider = null;

  async function api(path, options) {
    const res = await fetch(path, options);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body?.error?.message || `Request failed (${res.status})`);
    }
    return res.status === 204 ? null : res.json();
  }

  function setStatus(id, text, isError = false) {
    $(id).textContent = text;
    $(id).classList.toggle("error", isError);
  }

  async function init() {
    try {
      const [health, role] = await Promise.all([api("/api/health"), api("/api/role")]);
      provider = health.llm_default;
      if (!health.providers[provider]?.configured) provider = "mock";
      $("role-card").textContent = `Target role: ${role.title}`;
      setStatus("status-strip", `LLM mode: ${provider} (placeholder UI)`);
    } catch (err) {
      setStatus("status-strip", err.message, true);
    }
    $("start-btn").addEventListener("click", start);
    $("sample-btn").addEventListener("click", async () => {
      try {
        window.renderReport(await api("/api/sample-report"));
      } catch (err) {
        setStatus("status-strip", err.message, true);
      }
    });
  }

  async function start() {
    questions = await api("/api/questions");
    answers = [];
    index = 0;
    $("start").hidden = true;
    $("interview").hidden = false;
    showQuestion();
  }

  function showQuestion() {
    const q = questions[index];
    $("progress").textContent = `Question ${index + 1} of 8`; // 7 fixed + 1 follow-up
    $("question-panel").textContent = q.text;
    const panel = $("answer-panel");
    panel.replaceChildren();
    const box = document.createElement("textarea");
    box.setAttribute("aria-label", "Your answer");
    const next = document.createElement("button");
    next.className = "primary";
    next.textContent = "Next";
    next.disabled = true;
    box.addEventListener("input", () => (next.disabled = !box.value.trim()));
    next.addEventListener("click", () => submitAnswer(q, box.value.trim()));
    panel.append(box, next);
    box.focus();
  }

  async function submitAnswer(q, text) {
    answers.push({
      question_id: q.id, dimension_id: q.dimension_id, question: q.text,
      transcript: text, source: "typed",
    });
    index += 1;
    try {
      if (index < questions.length) return showQuestion();
      if (q.id !== "followup") {
        setStatus("interview-status", "Thinking of a follow-up question…");
        const res = await api("/api/follow-up", jsonBody({ provider, answers }));
        questions.push(res.question);
        setStatus("interview-status", "");
        return showQuestion();
      }
      setStatus("interview-status", "Assessing your answers…");
      const report = await api("/api/assess", jsonBody({ provider, answers }));
      window.renderReport(report);
    } catch (err) {
      setStatus("interview-status", err.message, true);
    }
  }

  const jsonBody = (data) => ({
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  document.addEventListener("DOMContentLoaded", init);
})();
