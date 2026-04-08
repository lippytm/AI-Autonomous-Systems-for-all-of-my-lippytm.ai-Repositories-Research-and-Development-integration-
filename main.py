"""CLI entry-point for the AI Autonomous Systems platform.

Usage::

    python main.py --config config/config.yaml --mode once
    python main.py --config config/config.yaml --mode qa
    python main.py --config config/config.yaml --mode content
"""

from __future__ import annotations

import argparse
import logging
import sys

from src.orchestrator import Orchestrator


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=getattr(logging, level.upper(), logging.INFO),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="lippytm.ai — AI Autonomous Systems platform",
    )
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Path to the YAML configuration file (default: config/config.yaml).",
    )
    parser.add_argument(
        "--mode",
        choices=["once", "qa", "content", "ads"],
        default="once",
        help=(
            "Execution mode: "
            "'once' runs a full cycle; "
            "'qa' runs QA checks only; "
            "'content' runs content generation only; "
            "'ads' runs advertising campaigns only."
        ),
    )
    parser.add_argument(
        "--topics",
        nargs="*",
        default=[],
        help="Advertising topics (used with --mode ads).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO).",
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Root directory of the project for QA checks (default: .).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.log_level)

    try:
        orch = Orchestrator.from_config(args.config, project_root=args.project_root)
    except FileNotFoundError:
        logging.error("Config file not found: %s", args.config)
        return 1

    if args.mode == "once":
        result = orch.run_once()
        print(result)
    elif args.mode == "qa":
        results = orch.run_qa_only()
        for r in results:
            status = "PASS" if r.passed else "FAIL"
            print(f"[{status}] {r.name}: {r.message}")
        if not orch.qa_monitor.all_passed(results):
            return 1
    elif args.mode == "content":
        items = orch.run_content_only()
        for item in items:
            print(f"[{item.platform}] {item.title}")
    elif args.mode == "ads":
        if not args.topics:
            logging.error("--topics is required with --mode ads.")
            return 1
        campaigns = orch.run_ads_only(args.topics)
        for c in campaigns:
            print(f"[{c.platform}] {c.name} (${c.budget_usd:.2f})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
