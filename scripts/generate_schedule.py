#!/usr/bin/env python3
"""Generate a reproducible blocked-randomized experiment schedule."""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path


LOAD_LEVELS = (0, 25, 50, 75, 100)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a schedule in which every repetition block contains each "
            "neighboring-VM CPU-load condition exactly once."
        )
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=10,
        help="Number of runs per condition (default: 10).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20260914,
        help="Random seed recorded for reproducibility (default: 20260914).",
    )
    parser.add_argument(
        "--blocks-per-session",
        type=int,
        default=5,
        help="Suggested number of five-condition blocks per session (default: 5).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("experiments/formal_v1_schedule.csv"),
        help="Output CSV path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.repetitions < 1:
        raise SystemExit("ERROR: --repetitions must be at least 1.")
    if args.blocks_per_session < 1:
        raise SystemExit("ERROR: --blocks-per-session must be at least 1.")

    rng = random.Random(args.seed)
    rows: list[dict[str, int]] = []
    sequence = 1

    for block in range(1, args.repetitions + 1):
        order = list(LOAD_LEVELS)
        rng.shuffle(order)
        session = ((block - 1) // args.blocks_per_session) + 1

        for position, load in enumerate(order, start=1):
            rows.append(
                {
                    "sequence": sequence,
                    "session": session,
                    "block": block,
                    "position_in_block": position,
                    "load_percent": load,
                    "run_number": block,
                }
            )
            sequence += 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=rows[0].keys(),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} trials to {args.output}")
    print(f"Conditions: {', '.join(f'{load}%' for load in LOAD_LEVELS)}")
    print(f"Runs per condition: {args.repetitions}")
    print(f"Seed: {args.seed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
