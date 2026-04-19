from __future__ import annotations

import argparse
import sys

from .config import build_config
from .runner import CatalogRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gg_eff_agent_cataloger",
        description="Catalog AI agent repositories and README/tool hygiene.",
    )

    parser.add_argument("--org", help="GitHub organization name")
    parser.add_argument("--repos", help="Comma-separated repository list")
    parser.add_argument("--discover", action="store_true", default=None, help="Enable discovery mode")
    parser.add_argument("--keywords", help="Comma-separated discovery keywords")
    parser.add_argument("--config", dest="config_file", help="Path to YAML config file")
    parser.add_argument("--allowed-tools", dest="allowed_tools_file", help="Path to allowed tools YAML")
    parser.add_argument("--out", help="Output directory", default=None)
    parser.add_argument("--clone-dir", help="Optional clone working directory", default=None)
    parser.add_argument(
        "--local-repos-dir",
        default=None,
        help="Local root directory containing already-cloned/downloaded repositories",
    )
    parser.add_argument("--apply", action="store_true", default=None, help="Enable apply mode")
    parser.add_argument("--pr", action="store_true", default=None, help="Open PRs in apply mode")
    parser.add_argument(
        "--privacy-safe-logging",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable privacy-safe logging mode",
    )
    parser.add_argument("--token-env", default=None, help="Environment variable containing GitHub token")
    parser.add_argument("--github-base-url", default=None, help="GitHub API base URL (for GH Enterprise)")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = build_config(args)
        runner = CatalogRunner(config)
        return runner.run()
    except Exception as exc:
        print(f"[gg_eff_agent_cataloger] ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

