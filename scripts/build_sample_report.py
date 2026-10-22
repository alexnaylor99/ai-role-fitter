"""Regenerate samples/sample_report.json from the fictional sample answers.

Usage: make sample PROVIDER=mock|claude|ollama
"""

from __future__ import annotations

import argparse
import json

from fastapi.testclient import TestClient

from app.config import ROOT
from app.main import app

SAMPLES = ROOT / "samples"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default="mock", choices=["mock", "claude", "ollama"])
    args = parser.parse_args()

    answers = json.loads((SAMPLES / "sample_answers.json").read_text(encoding="utf-8"))
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        res = client.post("/api/assess", json={"provider": args.provider, "answers": answers})
    if res.status_code != 200:
        raise SystemExit(f"Failed: {res.status_code} {res.text}")
    (SAMPLES / "sample_report.json").write_text(json.dumps(res.json(), indent=2) + "\n")
    fit = res.json()["role_fit"]
    print(f"Wrote samples/sample_report.json — {fit['fit_percent']}% ({fit['band']})")


if __name__ == "__main__":
    main()
