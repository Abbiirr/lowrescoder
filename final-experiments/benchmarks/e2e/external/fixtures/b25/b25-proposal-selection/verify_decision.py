"""Verify that the benchmark decision selected the strongest proposal."""

from __future__ import annotations

from pathlib import Path


def main() -> None:
    text = Path("decision.md").read_text(encoding="utf-8").lower()
    required_fragments = [
        "selected proposal: b",
        "idempotent",
        "rollback",
        "index",
    ]
    missing = [fragment for fragment in required_fragments if fragment not in text]
    if missing:
        raise SystemExit(f"Missing expected rationale fragments: {missing}")
    print("PASS")


if __name__ == "__main__":
    main()
