"""
Replay harness — re-parse saved fixtures without running the proxy.

Usage:
  python replay_harness.py
  python replay_harness.py --fixture fixtures/anthropic_stream.json
"""

import argparse
import json
from pathlib import Path

from parsers import event_from_fixture


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def run_fixture(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    event, drift = event_from_fixture(
        tool=data["tool"],
        request_text=data["request"],
        response_text=data["response"],
        content_type=data.get("content_type", "application/json"),
        url=data.get("url", f"fixture://{path.name}"),
    )

    print(f"\n--- {path.name} ---")
    if drift:
        print(f"  schema drift: {drift}")
    print(f"  tool: {event.tool} | model: {event.request_model}")
    print(f"  prompt ({event.tokens_in} est. tokens): {(event.prompt or '')[:80]}...")
    print(f"  response ({event.tokens_out} est. tokens): {(event.response_content or '')[:80]}...")
    print(f"  cost estimate: ${event.cost_estimate}")


def main():
    parser = argparse.ArgumentParser(description="Replay parser against saved fixtures")
    parser.add_argument("--fixture", type=Path, help="Single fixture JSON file")
    args = parser.parse_args()

    paths = [args.fixture] if args.fixture else sorted(FIXTURES_DIR.glob("*.json"))
    if not paths:
        print("No fixtures found. Add JSON files to fixtures/")
        return

    for path in paths:
        run_fixture(path)


if __name__ == "__main__":
    main()
