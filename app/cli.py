from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from app.bot.messages import render_status
from app.config import get_settings
from app.jobs.check_lists import (
    estimate_from_fixture,
    estimate_from_live,
    estimate_relative_competitions,
)
from app.rgrtu.parser import parse_fixture_file
from app.rgrtu.json_adapter import RgrtuLivewireAdapter


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="Run a local admission estimate")
    check.add_argument("--score", type=int, default=None)
    check.add_argument("--code", default=None, help="RGRTU service entrant code")
    check.add_argument(
        "--relative",
        action="store_true",
        help="Estimate with higher-priority filtering",
    )
    check.add_argument(
        "--debug",
        action="store_true",
        help="Print detailed calculation output",
    )
    check.add_argument("--fixture", type=Path, default=None)
    check.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS verification for local checks behind an intercepting proxy",
    )

    discover = subparsers.add_parser("discover", help="Discover public RGRTU subject ids")
    discover.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS verification for local discovery behind an intercepting proxy",
    )

    args = parser.parse_args()
    if args.command == "check":
        settings = get_settings()
        if args.insecure:
            settings.rgrtu_verify_ssl = False
        score = args.score if args.score is not None else settings.total_default_score
        if args.fixture is not None:
            if args.relative:
                estimates = estimate_relative_competitions(
                    parse_fixture_file(str(args.fixture)),
                    score,
                    entrant_code=args.code,
                )
            else:
                estimates = estimate_from_fixture(score, args.fixture)
        else:
            estimates = asyncio.run(
                estimate_from_live(
                    score,
                    settings,
                    entrant_code=args.code,
                    relative=args.relative,
                )
            )
        print(
            render_status(
                estimates,
                score=score,
                entrant_code=args.code,
                relative=args.relative,
                debug=args.debug,
                tz=settings.timezone,
            )
        )
    elif args.command == "discover":
        asyncio.run(_discover(insecure=args.insecure))


async def _discover(*, insecure: bool = False) -> None:
    settings = get_settings()
    if insecure:
        settings.rgrtu_verify_ssl = False
    discovery = await RgrtuLivewireAdapter(settings).discover()
    print(f"campaign_id: {discovery.campaign_id}")
    print(f"component: {discovery.component_name} / {discovery.livewire_id}")
    for subject_id, title in discovery.subjects.items():
        if title.startswith(("01.03.02", "02.03.02", "09.03.01", "09.03.02", "09.03.03")):
            print(f"{subject_id}: {title}")


if __name__ == "__main__":
    main()
