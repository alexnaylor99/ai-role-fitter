# Demo runbook

How to run the AI Role Fitter live in the ElevenLabs FDE interview, with fallbacks for
everything that can go wrong. The 5-minute script itself is in [SPEC §15](SPEC.md).

## The plan in one line

**Run the interview live in Claude mode; show local (private) mode from a recording,** then
explain the trade-off. On a 2-core 2017 laptop the local model takes 2–4 minutes per report,
and longer if anything else is running, which is too slow and too variable to wait for live.

## Before the interview (day before)

- [ ] **Record local mode** (SPEC Phase 3.6): close everything else, run one full interview in
      Local mode with `?demo=1`, and screen-record it (⌘⇧5). Keep it short: trim the waiting.
- [ ] **Warm the question audio cache:** do one real-voice run so the 7 questions are saved in
      `tts_cache/`. After that, live runs only spend ElevenLabs credits on the follow-up
      question and on transcribing your answers.
      Budget: 10,000 credits in total, and the first run costs ~800.
- [ ] **Check the keys:** the Claude key in `.env` has a spend limit set; the ElevenLabs key works.
- [ ] `make check` passes and `make dev` starts cleanly.
- [ ] Open the sample report once (start screen → *View sample report*) as a no-network backup.

## Right before (10 minutes)

- [ ] Quit every app you don't need, including other Claude Code sessions. The local model and
      the browser share 2 CPU cores and 8GB of memory.
- [ ] Plug in the charger (macOS slows the CPU on battery).
- [ ] `make dev`, open http://127.0.0.1:8000. The status strip should show Claude, Voice and
      Local model as ready.
- [ ] Have the recording and the repo open in other tabs.

## During the demo

| Step | Mode | If it fails |
|---|---|---|
| Answer 2–3 questions by voice | Claude + ElevenLabs | Type the answer instead (always available) |
| Skip ahead with pre-filled answers | `?demo=1` | — |
| Show the report | Claude (~10–20 s, ~$0.002) | *View sample report* (no network needed) |
| Explain privacy mode | Play the local-mode recording | — |
| Show the code | `app/roles/elevenlabs_fde.json`, `app/fit.py`, eval output | — |

Running the same answers twice gives an instant result at no cost (the in-memory response
cache). Use that if you need to show the report again.

## Talking points for local mode

- **Privacy:** answers never leave the laptop in local mode. Only speech-to-text goes to
  ElevenLabs.
- **Hardware is the limit:** the same model writes 850 to 3,000+ tokens for the same answers. On
  2 cores that is 2–6 minutes, and it slows further when other apps are busy. That is why local
  mode asks for a shorter report, caps its length and says "about 3 minutes".
- **Quality trade-off (measured):** on the 3 eval personas, Claude (Haiku 5.5) put 20/21
  scores in range and got all 3 fit bands right. The local 1.5B model, with the shorter
  reports it needs to finish in ~2 minutes, put 15/21 in range and got 1/3 bands right. It is
  generous: it scored the novice at 63% (expected under 50%) and the practitioner at 100%
  (Claude: 83%). Local mode is a privacy option, not the accurate one.
- **What a customer would do:** run local mode on better hardware (a GPU or Apple Silicon), or a
  larger local model, or a private cloud deployment. The provider is a config switch.
