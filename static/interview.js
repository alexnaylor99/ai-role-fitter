// Start screen and interview flow (SPEC §4 steps 1-4). Plain JS, no build step.
// Everything that comes from the server or an LLM is rendered with textContent.
(() => {
  const $ = (id) => document.getElementById(id);
  const MAX_RECORD_S = 120;
  const TOTAL_QUESTIONS = 8; // 7 fixed + 1 adaptive follow-up
  const DIMENSION_NAMES = {
    breadth: "Tool and model breadth",
    prompting: "Prompting and context",
    verification: "Critical evaluation",
    building: "Building with AI APIs",
    voice_audio: "Voice and audio AI",
    responsible: "Responsible use",
    customer_value: "Turning AI into value",
  };
  const MODES = [
    { id: "claude", label: "Claude" },
    { id: "ollama", label: "Local (Qwen 2.5 1.5B)" },
    { id: "mock", label: "Mock" },
  ];
  const ESTIMATES = {
    claude: "This usually takes about 20 seconds.",
    ollama: "Running on this device, this usually takes about 2 minutes.",
    mock: "This should only take a moment.",
  };

  const state = {
    health: null,
    provider: "mock",
    voiceConfigured: false,
    questions: [],
    answers: [],
    index: 0,
    metrics: { stt_ms: [], tts_ms: [] },
    demoAnswers: null,
    audio: null,
    audioUrl: null,
    ttsToken: 0,
    recorder: null,
  };

  // --- Helpers ---------------------------------------------------------------------

  function el(tag, props = {}, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(props)) {
      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = value;
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value);
    }
    node.append(...children.filter((c) => c != null));
    return node;
  }

  async function api(path, options) {
    let res;
    try {
      res = await fetch(path, options);
    } catch {
      throw new Error("Couldn't reach the app. Check that it is still running, then try again.");
    }
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body?.error?.message || `Something went wrong (${res.status}).`);
    }
    return res.status === 204 ? null : res.json();
  }

  const jsonBody = (data) => ({
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  function setStatus(id, text, isError = false) {
    const node = $(id);
    node.textContent = text;
    node.classList.toggle("error", isError);
  }

  const formatTime = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

  // --- Start screen ----------------------------------------------------------------

  function renderRoleCard(role) {
    const top = [...role.requirements]
      .sort((a, b) => b.weight - a.weight || b.target - a.target)
      .slice(0, 4);
    $("role-card").replaceChildren(
      el("p", { class: "eyebrow", text: "Target role" }),
      el("h3", { class: "role-title", text: role.title }),
      el("p", { class: "muted", text: role.summary }),
      el("h4", { text: "What the role weights most" }),
      el(
        "ul",
        { class: "requirements" },
        ...top.map((r) =>
          el(
            "li",
            {},
            el("strong", { text: DIMENSION_NAMES[r.dimension_id] || r.dimension_id }),
            el("span", { class: "muted", text: ` — ${r.why}` }),
          ),
        ),
      ),
    );
  }

  function modeAvailable(id) {
    const info = state.health?.providers?.[id];
    if (!info?.configured) return false;
    return id !== "ollama" || info.reachable !== false;
  }

  function modeNote(id) {
    if (modeAvailable(id)) return "";
    if (id === "claude") return "not set up";
    if (id === "ollama") return state.health?.providers?.ollama?.configured ? "not running" : "not set up";
    return "";
  }

  function renderModePicker() {
    const defaultMode = state.health.llm_default;
    state.provider = modeAvailable(defaultMode) ? defaultMode : "mock";
    const group = el("fieldset", { class: "mode-group" }, el("legend", { text: "Assessment mode" }));
    for (const mode of MODES) {
      const available = modeAvailable(mode.id);
      const input = el("input", { type: "radio", name: "mode", value: mode.id });
      input.checked = mode.id === state.provider;
      input.disabled = !available;
      input.addEventListener("change", () => {
        state.provider = mode.id;
        updatePrivacyNote();
      });
      const note = modeNote(mode.id);
      group.append(
        el(
          "label",
          { class: `mode-option${available ? "" : " disabled"}` },
          input,
          el("span", { text: mode.label }),
          note ? el("span", { class: "muted", text: ` (${note})` }) : null,
        ),
      );
    }
    $("mode-picker").replaceChildren(
      group,
      el("p", {
        id: "privacy-note",
        class: "note",
        text: "Answers stay on this device. Speech is transcribed by ElevenLabs.",
        hidden: "",
      }),
    );
    updatePrivacyNote();
  }

  function updatePrivacyNote() {
    const note = $("privacy-note");
    if (note) note.hidden = state.provider !== "ollama";
  }

  function renderStatusStrip() {
    const h = state.health;
    const part = (label, ok, detail) =>
      el("li", { class: ok ? "ok" : "off", text: `${label}: ${detail}` });
    const claude = h.providers.claude;
    const ollama = h.providers.ollama;
    $("status-strip").replaceChildren(
      el(
        "ul",
        { class: "status-list" },
        part("Claude", claude.configured, claude.configured ? "ready" : "not set up"),
        part(
          "Local model",
          ollama.configured && ollama.reachable,
          ollama.reachable ? "running" : ollama.configured ? "not running" : "not set up",
        ),
        part("Mock", true, "ready"),
        part("Voice", h.voice.configured, h.voice.configured ? "ready" : "typed answers only"),
      ),
    );
  }

  async function init() {
    $("start-btn").addEventListener("click", start);
    $("sample-btn").addEventListener("click", viewSample);
    try {
      const [health, role] = await Promise.all([api("/api/health"), api("/api/role")]);
      state.health = health;
      state.voiceConfigured = Boolean(health.voice?.configured);
      renderRoleCard(role);
      renderModePicker();
      renderStatusStrip();
    } catch (err) {
      setStatus("status-strip", err.message, true);
    }
    if (new URLSearchParams(location.search).get("demo") === "1") {
      try {
        state.demoAnswers = await api("/api/demo-answers");
      } catch {
        state.demoAnswers = null; // optional helper: carry on without it
      }
    }
  }

  async function viewSample() {
    const btn = $("sample-btn");
    btn.disabled = true;
    try {
      window.renderReport(await api("/api/sample-report"));
    } catch (err) {
      setStatus("status-strip", err.message, true);
    } finally {
      btn.disabled = false;
    }
  }

  // --- Interview -------------------------------------------------------------------

  async function start() {
    const btn = $("start-btn");
    btn.disabled = true;
    try {
      state.questions = await api("/api/questions");
    } catch (err) {
      setStatus("status-strip", err.message, true);
      btn.disabled = false;
      return;
    }
    btn.disabled = false;
    state.answers = [];
    state.index = 0;
    state.metrics = { stt_ms: [], tts_ms: [] };
    $("start").hidden = true;
    $("interview").hidden = false;
    showQuestion();
  }

  function demoText(q, index) {
    const list = state.demoAnswers;
    if (!Array.isArray(list)) return "";
    const match = list.find((a) => a.question_id === q.id) || list[index];
    return match?.transcript || "";
  }

  function showQuestion() {
    const q = state.questions[state.index];
    stopAudio();
    setStatus("interview-status", "");
    $("progress").textContent = `Question ${state.index + 1} of ${TOTAL_QUESTIONS}`;

    const replay = el("button", { type: "button", text: "Replay question", hidden: "" });
    replay.addEventListener("click", () => speak(q.text));
    $("question-panel").replaceChildren(
      el("p", { class: "question-text", text: q.text }),
      replay,
    );

    const box = el("textarea", { id: "answer-box", "aria-label": "Your answer" });
    box.placeholder = "Record your answer, or type it here.";
    box.value = demoText(q, state.index);
    const next = el("button", { type: "button", class: "primary", text: "Next" });
    const voiceNote = el("p", { class: "note", id: "voice-note", role: "status" });
    const ctx = { q, box, next, voiceNote, replay, fromVoice: false };

    next.disabled = !box.value.trim();
    box.addEventListener("input", () => (next.disabled = !box.value.trim()));
    next.addEventListener("click", () => submitAnswer(ctx));

    const controls = el("div", { class: "actions" });
    if (state.voiceConfigured && navigator.mediaDevices?.getUserMedia && window.MediaRecorder) {
      controls.append(buildRecorder(ctx));
    } else {
      voiceNote.textContent = state.voiceConfigured
        ? "Recording isn't supported in this browser. Please type your answer."
        : "Voice isn't set up, so please type your answer.";
    }

    $("answer-panel").replaceChildren(box, voiceNote, controls, next);
    box.focus();
    speak(q.text, replay);
  }

  // --- Text to speech --------------------------------------------------------------

  function stopAudio() {
    state.ttsToken += 1; // ignores any TTS request still in flight
    if (state.audio) state.audio.pause();
    if (state.audioUrl) URL.revokeObjectURL(state.audioUrl);
    state.audio = null;
    state.audioUrl = null;
  }

  // Question audio costs ElevenLabs credits, so each question is fetched once: kept in memory
  // for Replay and in the Cache API so a page reload doesn't synthesise it again.
  const ttsMemory = new Map();
  const TTS_CACHE = "tts-v1";

  async function ttsBlob(text) {
    if (ttsMemory.has(text)) return ttsMemory.get(text);
    const key = `/tts-cache/${encodeURIComponent(text)}`;
    try {
      const hit = await (await caches.open(TTS_CACHE)).match(key);
      if (hit) {
        const cached = await hit.blob();
        ttsMemory.set(text, cached);
        return cached;
      }
    } catch {
      // Cache API unavailable: fall through to the network
    }
    const started = performance.now();
    const res = await fetch("/api/tts", jsonBody({ text }));
    if (res.status === 204 || !res.ok) return null;
    const blob = await res.blob();
    state.metrics.tts_ms.push(Math.round(performance.now() - started));
    ttsMemory.set(text, blob);
    try {
      await (await caches.open(TTS_CACHE)).put(key, new Response(blob));
    } catch {
      // not cached across reloads, still cached in memory
    }
    return blob;
  }

  async function speak(text, replayButton) {
    stopAudio();
    const token = state.ttsToken;
    try {
      const blob = await ttsBlob(text);
      if (!blob || token !== state.ttsToken) return; // no audio is fine, never an error
      state.audioUrl = URL.createObjectURL(blob);
      state.audio = new Audio(state.audioUrl);
      if (replayButton) replayButton.hidden = false;
      await state.audio.play().catch(() => {}); // autoplay may be blocked: Replay still works
    } catch {
      // TTS is a nicety: the question is already on screen
    }
  }

  // --- Recording -------------------------------------------------------------------

  function buildRecorder(ctx) {
    const button = el("button", { type: "button", text: "Record" });
    const timer = el("span", { class: "timer muted", "aria-hidden": "true" });
    const wrap = el("div", { class: "recorder" }, button, timer);
    let session = null;

    button.addEventListener("click", async () => {
      if (session) return session.stop();
      stopAudio();
      ctx.voiceNote.textContent = "";
      let stream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch {
        ctx.voiceNote.textContent =
          "Microphone access was blocked, so please type your answer instead.";
        button.disabled = true;
        return;
      }
      session = beginRecording(stream, ctx, button, timer, () => {
        session = null;
      });
    });
    return wrap;
  }

  function beginRecording(stream, ctx, button, timer, onDone) {
    const mimeType = ["audio/webm;codecs=opus", "audio/webm"].find((t) =>
      MediaRecorder.isTypeSupported?.(t),
    );
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    const chunks = [];
    let seconds = 0;
    let ticker;

    const cleanup = () => {
      clearInterval(ticker);
      stream.getTracks().forEach((t) => t.stop());
      state.recorder = null;
    };
    recorder.addEventListener("dataavailable", (e) => e.data.size && chunks.push(e.data));
    recorder.addEventListener("stop", async () => {
      cleanup();
      onDone();
      timer.textContent = "";
      button.textContent = "Record";
      button.classList.remove("recording");
      const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
      await transcribe(blob, ctx, button);
    });

    recorder.start();
    state.recorder = recorder;
    button.textContent = "Stop";
    button.classList.add("recording");
    timer.textContent = `0:00 / ${formatTime(MAX_RECORD_S)}`;
    ctx.voiceNote.textContent = "Recording…";
    ticker = setInterval(() => {
      seconds += 1;
      timer.textContent = `${formatTime(seconds)} / ${formatTime(MAX_RECORD_S)}`;
      if (seconds >= MAX_RECORD_S) {
        ctx.voiceNote.textContent = "Reached the 2-minute limit, so recording stopped.";
        recorder.stop();
      }
    }, 1000);

    return { stop: () => recorder.state !== "inactive" && recorder.stop() };
  }

  async function transcribe(blob, ctx, button) {
    ctx.voiceNote.textContent = "Transcribing…";
    button.disabled = true;
    ctx.next.disabled = true;
    try {
      const form = new FormData();
      form.append("audio", blob, "answer.webm");
      const res = await api("/api/transcribe", { method: "POST", body: form });
      const text = (res.text || "").trim();
      if (!text) {
        ctx.voiceNote.textContent = "I couldn't hear anything. Try again, or type your answer.";
      } else {
        ctx.box.value = ctx.box.value.trim() ? `${ctx.box.value.trim()} ${text}` : text;
        ctx.fromVoice = true;
        state.metrics.stt_ms.push(res.duration_ms);
        ctx.voiceNote.textContent = "Transcribed. You can edit the text before continuing.";
      }
    } catch (err) {
      ctx.voiceNote.textContent = `${err.message} You can type your answer instead.`;
    } finally {
      button.disabled = false;
      ctx.next.disabled = !ctx.box.value.trim();
      ctx.box.focus();
    }
  }

  // --- Submitting ------------------------------------------------------------------

  function submitAnswer(ctx) {
    if (state.recorder && state.recorder.state !== "inactive") state.recorder.stop();
    const { q, box } = ctx;
    state.answers.push({
      question_id: q.id,
      dimension_id: q.dimension_id ?? null,
      question: q.text,
      transcript: box.value.trim(),
      source: ctx.fromVoice ? "voice" : "typed",
    });
    state.index += 1;
    advance();
  }

  // Runs after each answer; also used by Retry, so answers already given are never lost.
  async function advance() {
    try {
      if (state.index < state.questions.length) return showQuestion();
      if (state.questions.length < TOTAL_QUESTIONS) {
        lockInterview("Thinking of a follow-up question…");
        const res = await api(
          "/api/follow-up",
          jsonBody({ provider: state.provider, answers: state.answers }),
        );
        state.questions.push(res.question);
        return showQuestion();
      }
      lockInterview(`Assessing your answers. ${ESTIMATES[state.provider] || ""}`);
      const report = await api(
        "/api/assess",
        jsonBody({
          provider: state.provider,
          answers: state.answers,
          client_metrics: state.metrics,
        }),
      );
      window.renderReport(report);
    } catch (err) {
      showRetry(err.message);
    }
  }

  function lockInterview(message) {
    stopAudio();
    $("question-panel").replaceChildren();
    $("answer-panel").replaceChildren(
      el("p", { class: "busy", role: "status", text: message }),
      el("div", { class: "spinner", "aria-hidden": "true" }),
    );
    setStatus("interview-status", "");
  }

  function showRetry(message) {
    const retry = el("button", { type: "button", class: "primary", text: "Try again" });
    retry.addEventListener("click", () => advance());
    $("answer-panel").replaceChildren(
      el("p", { class: "error", role: "alert", text: message }),
      el("p", { class: "muted", text: "Your answers are safe. Nothing has been lost." }),
      el("div", { class: "actions" }, retry),
    );
    setStatus("interview-status", "");
    retry.focus();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
