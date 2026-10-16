"""Evaluation harness: score the fictional personas and compare with expected ranges (SPEC §13).

Usage: make eval PROVIDER=mock|claude|ollama

A report, not a gate: it always exits 0. Each persona's 7 fixed answers plus its follow-up
go through the provider's assess(); the role fit comes from app/fit.py, as in the app.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from app.config import get_settings
from app.contracts import DIMENSION_IDS, Answer, AppError, RoleProfile
from app.fit import compute_role_fit, load_role
from app.llm import get_llm
from app.rubric import level_for, overall_score

PERSONAS_DIR = Path(__file__).resolve().parent / "fixtures" / "personas"
ORDER = ["novice", "practitioner", "expert"]


def load_personas() -> list[dict]:
    paths = sorted(PERSONAS_DIR.glob("*.json"))
    personas = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    personas.sort(key=lambda p: ORDER.index(p["id"]) if p["id"] in ORDER else len(ORDER))
    for p in personas:
        p["answers"] = [Answer.model_validate(a) for a in p["answers"]]
    return personas


async def run_persona(llm, persona: dict, role: RoleProfile) -> dict:
    answers: list[Answer] = persona["answers"]
    fixed = [a for a in answers if a.question_id != "followup"]

    start = time.perf_counter()
    _, follow_up_dim, _ = await llm.follow_up(fixed, role)
    follow_up_ms = int((time.perf_counter() - start) * 1000)

    start = time.perf_counter()
    assessment, usage = await llm.assess(answers, role)
    assess_ms = int((time.perf_counter() - start) * 1000)

    fit = compute_role_fit(assessment, role)
    scores = {d.dimension_id: d.score for d in assessment.dimensions}
    in_range = {
        d: persona["expected"][d][0] <= scores[d] <= persona["expected"][d][1]
        for d in DIMENSION_IDS
    }
    return {
        "scores": scores,
        "in_range": in_range,
        "fit_percent": fit.fit_percent,
        "band": fit.band,
        "level": level_for(overall_score(assessment)),
        "follow_up_dim": follow_up_dim,
        "follow_up_ms": follow_up_ms,
        "assess_ms": assess_ms,
        "tokens": (usage.input_tokens, usage.output_tokens),
        "quotes": sum(1 for d in assessment.dimensions if d.evidence_quote),
    }


def _seconds(ms: int) -> str:
    return f"{ms / 1000:.1f}s"


def print_report(provider: str, model: str, personas: list[dict], results: dict) -> None:
    print(f"\nEval: provider={provider} model={model}\n")

    # Dimension scores against expected ranges, one column per persona.
    ids = [p["id"] for p in personas]
    header = f"{'dimension':<16}" + "".join(f"{pid:>18}" for pid in ids)
    print(header)
    print("-" * len(header))
    for d in DIMENSION_IDS:
        row = f"{d:<16}"
        for p in personas:
            r = results.get(p["id"])
            lo, hi = p["expected"][d]
            if isinstance(r, dict):
                mark = "ok" if r["in_range"][d] else "MISS"
                cell = f"{r['scores'][d]} [{lo}-{hi}] {mark}"
            else:
                cell = "error"
            row += f"{cell:>18}"
        print(row)

    # One summary line per persona.
    print()
    cols = (
        f"{'persona':<13}{'in range':>9}{'fit %':>7}  {'band':<15}{'expected':<15}"
        f"{'band ok':<8}{'level':<13}{'follow-up':<16}{'assess':>8}{'f-up':>7}"
    )
    print(cols)
    print("-" * len(cols))
    total_hits = total_dims = band_hits = 0
    for p in personas:
        r = results.get(p["id"])
        if not isinstance(r, dict):
            print(f"{p['id']:<13}error: {r}")
            continue
        hits = sum(r["in_range"].values())
        band_ok = r["band"] == p["expected_band"]
        total_hits += hits
        total_dims += len(DIMENSION_IDS)
        band_hits += band_ok
        print(
            f"{p['id']:<13}{f'{hits}/7':>9}{r['fit_percent']:>7}  {r['band']:<15}"
            f"{p['expected_band']:<15}{'yes' if band_ok else 'NO':<8}{r['level']:<13}"
            f"{r['follow_up_dim'] or '-':<16}{_seconds(r['assess_ms']):>8}"
            f"{_seconds(r['follow_up_ms']):>7}"
        )

    if total_dims:
        pct = round(100 * total_hits / total_dims)
        ran = total_dims // len(DIMENSION_IDS)
        print(
            f"\nScores in expected range: {total_hits}/{total_dims} ({pct}%). "
            f"Fit band matches: {band_hits}/{ran}."
        )
    tokens = [r["tokens"] for r in results.values() if isinstance(r, dict)]
    if any(i for i, _ in tokens):
        print(f"Tokens: {sum(i or 0 for i, _ in tokens)} in, {sum(o or 0 for _, o in tokens)} out.")


async def main_async(provider: str) -> None:
    settings = get_settings()
    role = load_role(settings.role_profile_path)
    try:
        llm = get_llm(provider, settings)
    except AppError as exc:
        print(f"Can't run the eval with provider '{provider}': {exc.message}")
        return

    personas = load_personas()
    results: dict[str, dict | str] = {}
    for persona in personas:
        try:
            results[persona["id"]] = await run_persona(llm, persona, role)
        except AppError as exc:
            results[persona["id"]] = exc.message
        except Exception as exc:  # a report, not a gate: show it and carry on
            results[persona["id"]] = f"{type(exc).__name__}: {exc}"
    print_report(provider, llm.model, personas, results)


def main() -> None:
    parser = argparse.ArgumentParser(description="Score the eval personas.")
    parser.add_argument("--provider", default="mock", choices=["mock", "claude", "ollama"])
    args = parser.parse_args()
    asyncio.run(main_async(args.provider))


if __name__ == "__main__":
    main()
