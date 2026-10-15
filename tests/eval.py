"""Evaluation harness — placeholder. T6 replaces this file (docs/tasks/T6-rubric-prompts-eval.md).

Usage: make eval PROVIDER=mock|claude|ollama
"""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default="mock", choices=["mock", "claude", "ollama"])
    args = parser.parse_args()
    print(f"Eval set not built yet (task T6). Provider requested: {args.provider}")


if __name__ == "__main__":
    main()
