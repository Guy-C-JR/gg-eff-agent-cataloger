from __future__ import annotations

import json
from pathlib import Path

from gg_eff_agent_cataloger.models import AppConfig
from gg_eff_agent_cataloger.runner import CatalogRunner


def _write_minimal_agent_repo(repo_dir: Path) -> None:
    (repo_dir / "src").mkdir(parents=True, exist_ok=True)

    readme = """
# EHR Agent

## Overview
Agent summary.

## Quickstart
Run app.

## Installation / Setup
Install dependencies.

## Configuration
Set environment variables.

## Tools & Data Sources
- `fetch_fhir_patient`: Reads from FHIR

## Examples
- Fetch patient 123

## Testing
pytest

## Safety / Compliance Notes
Follow privacy guardrails.

## Repository Structure
- src/

## Changelog / Versioning
Use tags.
"""

    source = """
from toolkit import ToolRegistry
ToolRegistry.register("fetch_fhir_patient", lambda x: x)
FHIR_URL = "https://ehr.internal/fhir"
"""

    (repo_dir / "README.md").write_text(readme, encoding="utf-8")
    (repo_dir / "src" / "agent.py").write_text(source, encoding="utf-8")


def test_local_mode_runs_without_github_token_and_resolves_main_suffix(tmp_path, monkeypatch) -> None:
    local_root = tmp_path / "local_repos"
    repo_dir = local_root / "ehr-ai-agent-main"
    _write_minimal_agent_repo(repo_dir)

    allowed_tools = tmp_path / "allowed_tools.yaml"
    allowed_tools.write_text(
        """
tools:
  - tool_id: fetch_fhir_patient
    tool_name: FetchFHIRPatient
    expected_data_sources: [FHIR API]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    out_dir = tmp_path / "catalog"

    config = AppConfig(
        org="local",
        repos=["ehr-ai-agent"],
        agents={},
        discover=False,
        keywords=["ehr"],
        out=str(out_dir),
        clone_dir=None,
        local_repos_dir=str(local_root),
        allowed_tools_file=str(allowed_tools),
        apply=False,
        pr=False,
        privacy_safe_logging=True,
        token_env="GITHUB_TOKEN",
    )

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    exit_code = CatalogRunner(config).run()

    assert exit_code == 0
    payload = json.loads((out_dir / "GG_EFF_AGENT_CATALOG.json").read_text(encoding="utf-8"))
    assert payload["repos_scanned"] == 1
    assert payload["agents"][0]["repo"] == "ehr-ai-agent"
    assert payload["agents"][0]["readme_status"] in {"ok", "needs_update"}

    issue_codes = {issue["code"] for issue in payload["agents"][0]["issues"]}
    assert "LOCAL_REPO_DIR_ALIAS" in issue_codes


def test_local_mode_discovery_filters_by_keywords(tmp_path, monkeypatch) -> None:
    local_root = tmp_path / "local_repos"
    _write_minimal_agent_repo(local_root / "ehr-ai-agent-main")
    _write_minimal_agent_repo(local_root / "misc-repo")

    allowed_tools = tmp_path / "allowed_tools.yaml"
    allowed_tools.write_text("tools: []\n", encoding="utf-8")

    out_dir = tmp_path / "catalog"

    config = AppConfig(
        org="local",
        repos=[],
        agents={},
        discover=True,
        keywords=["ehr"],
        out=str(out_dir),
        clone_dir=None,
        local_repos_dir=str(local_root),
        allowed_tools_file=str(allowed_tools),
        apply=False,
        pr=False,
        privacy_safe_logging=True,
        token_env="GITHUB_TOKEN",
    )

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    exit_code = CatalogRunner(config).run()

    assert exit_code == 0
    payload = json.loads((out_dir / "GG_EFF_AGENT_CATALOG.json").read_text(encoding="utf-8"))
    scanned_repos = [agent["repo"] for agent in payload["agents"]]
    assert scanned_repos == ["ehr-ai-agent"]


def _write_repo_missing_tools_section(repo_dir: Path) -> None:
    (repo_dir / "src").mkdir(parents=True, exist_ok=True)

    readme = """
# EHR Agent

## Overview
Agent summary.

## Quickstart
Run app.

## Installation / Setup
Install dependencies.

## Configuration
Set environment variables.

## Examples
- Fetch patient 123

## Testing
pytest

## Safety / Compliance Notes
Follow privacy guardrails.

## Repository Structure
- src/

## Changelog / Versioning
Use tags.
"""

    source = """
from toolkit import ToolRegistry
ToolRegistry.register("fetch_fhir_patient", lambda x: x)
FHIR_URL = "https://ehr.internal/fhir"
"""

    (repo_dir / "README.md").write_text(readme, encoding="utf-8")
    (repo_dir / "src" / "agent.py").write_text(source, encoding="utf-8")


def test_local_apply_reanalyzes_after_changes(tmp_path, monkeypatch) -> None:
    local_root = tmp_path / "local_repos"
    repo_dir = local_root / "ehr-ai-agent"
    _write_repo_missing_tools_section(repo_dir)

    allowed_tools = tmp_path / "allowed_tools.yaml"
    allowed_tools.write_text(
        """
tools:
  - tool_id: fetch_fhir_patient
    tool_name: FetchFHIRPatient
    expected_data_sources: [FHIR API]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    out_dir = tmp_path / "catalog"

    config = AppConfig(
        org="local",
        repos=["ehr-ai-agent"],
        agents={},
        discover=False,
        keywords=["ehr"],
        out=str(out_dir),
        clone_dir=None,
        local_repos_dir=str(local_root),
        allowed_tools_file=str(allowed_tools),
        apply=True,
        pr=False,
        privacy_safe_logging=True,
        token_env="GITHUB_TOKEN",
    )

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    exit_code = CatalogRunner(config).run()

    assert exit_code == 0

    payload = json.loads((out_dir / "GG_EFF_AGENT_CATALOG.json").read_text(encoding="utf-8"))
    agent = payload["agents"][0]

    assert "Tools & Data Sources" not in agent["required_sections"]["missing"]

    issue_codes = {issue["code"] for issue in agent["issues"]}
    assert "TOOLS_DATA_SOURCES_SECTION_MISSING" not in issue_codes
    assert "README_SECTIONS_MISSING" not in issue_codes

    readme_text = (repo_dir / "README.md").read_text(encoding="utf-8")
    assert "## Tools & Data Sources" in readme_text
