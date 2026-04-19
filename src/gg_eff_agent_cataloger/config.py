from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .constants import DEFAULT_AGENT_KEYWORDS
from .models import AppConfig


def parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def load_config_file(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("Config file must contain a top-level mapping")
    return data


def _set_if_not_none(target: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        target[key] = value


def build_config(args: argparse.Namespace) -> AppConfig:
    base = load_config_file(getattr(args, "config_file", None))

    if getattr(args, "org", None):
        base["org"] = args.org

    repos = parse_csv(getattr(args, "repos", None))
    if repos:
        base["repos"] = repos

    keywords = parse_csv(getattr(args, "keywords", None))
    if keywords:
        base["keywords"] = keywords

    _set_if_not_none(base, "discover", getattr(args, "discover", None))
    _set_if_not_none(base, "out", getattr(args, "out", None))
    _set_if_not_none(base, "allowed_tools_file", getattr(args, "allowed_tools_file", None))
    _set_if_not_none(base, "apply", getattr(args, "apply", None))
    _set_if_not_none(base, "pr", getattr(args, "pr", None))
    _set_if_not_none(base, "privacy_safe_logging", getattr(args, "privacy_safe_logging", None))
    _set_if_not_none(base, "token_env", getattr(args, "token_env", None))
    _set_if_not_none(base, "github_base_url", getattr(args, "github_base_url", None))
    _set_if_not_none(base, "clone_dir", getattr(args, "clone_dir", None))
    _set_if_not_none(base, "local_repos_dir", getattr(args, "local_repos_dir", None))

    if "keywords" not in base:
        base["keywords"] = DEFAULT_AGENT_KEYWORDS.copy()

    if "repos" not in base:
        base["repos"] = []

    if "agents" not in base:
        base["agents"] = {}

    if not base.get("org"):
        if base.get("local_repos_dir"):
            base["org"] = "local"
        else:
            raise ValueError("Organization is required. Use --org or set org in config file.")

    if base.get("apply") is not True:
        base["apply"] = False

    if base.get("apply") is False:
        base["pr"] = False

    try:
        return AppConfig(**base)
    except ValidationError as exc:
        raise ValueError(f"Invalid config: {exc}") from exc


def resolve_repo_targets(config: AppConfig) -> list[tuple[str, str]]:
    targets: list[tuple[str, str]] = []
    seen: set[str] = set()

    for agent_name, repo_name in config.agents.items():
        normalized = repo_name.strip()
        if normalized and normalized not in seen:
            targets.append((agent_name, normalized))
            seen.add(normalized)

    for repo_name in config.repos:
        normalized = repo_name.strip()
        if not normalized or normalized in seen:
            continue
        targets.append((guess_agent_name(normalized), normalized))
        seen.add(normalized)

    return targets


def guess_agent_name(repo_name: str) -> str:
    lower_name = repo_name.lower()
    mapping = {
        "ehr": "EHR",
        "phenotype": "Phenotype",
        "pgx": "PGX",
        "pmx": "PMX",
        "gwas": "GWAS",
        "rx": "Rx",
    }
    for key, label in mapping.items():
        if key in lower_name:
            return label
    return repo_name
