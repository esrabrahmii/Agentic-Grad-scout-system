#!/usr/bin/env python3
"""CLI entry point for grad-scout."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gradscout.models import SearchConstraints
from gradscout.utils.logging import configure_logging, get_logger

configure_logging()
logger = get_logger("cli")


def _prompt_constraints() -> SearchConstraints:
    print("\n=== grad-scout: Graduate Program Search ===\n")

    fields_raw = input("Fields of interest (comma-separated, e.g. 'machine learning, NLP'): ")
    fields = [f.strip() for f in fields_raw.split(",") if f.strip()]

    countries_raw = input("Countries (comma-separated, e.g. 'Germany, Netherlands') or Enter for all Europe: ")
    countries = [c.strip() for c in countries_raw.split(",") if c.strip()]

    fees_raw = input("Max fees EUR/year (Enter = free programs only, 0 = any): ").strip()
    if fees_raw == "0":
        max_fees = None
    elif fees_raw == "":
        max_fees = 0
    else:
        max_fees = int(fees_raw)

    level_raw = input("Level [masters/phd/both] (Enter = masters): ").strip() or "masters"
    year_raw = input("Start year (Enter = 2026): ").strip() or "2026"

    return SearchConstraints(
        fields=fields,
        countries=countries,
        max_fees_eur_per_year=max_fees if max_fees != 0 else None,
        level=level_raw,
        start_year=int(year_raw),
    )


async def run(constraints: SearchConstraints) -> None:
    from gradscout.graph import graph

    initial_state = {
        "constraints": constraints,
        "messages": [],
        "discovered_programs": [],
        "researched_programs": [],
        "ranked_programs": [],
        "research_index": 0,
        "errors": [],
        "final_table": "",
    }

    print("\nSearching... (this may take a few minutes)\n")
    final = await graph.ainvoke(initial_state)

    print("\n" + "=" * 80)
    print(final["final_table"])

    if final.get("errors"):
        print(f"\n{len(final['errors'])} errors encountered — see above table notes.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Search for graduate programs")
    parser.add_argument("--interactive", action="store_true", help="Prompt for constraints interactively")
    args = parser.parse_args()

    if args.interactive:
        constraints = _prompt_constraints()
    else:
        parser.print_help()
        return

    asyncio.run(run(constraints))


if __name__ == "__main__":
    main()
