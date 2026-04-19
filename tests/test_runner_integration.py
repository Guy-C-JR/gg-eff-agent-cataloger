from __future__ import annotations

import json
from pathlib import Path

import gg_eff_agent_cataloger.runner as runner_module
from gg_eff_agent_cataloger.git_ops import GitSyncResult
from gg_eff_agent_cataloger.github_client import RepoMetadata
from gg_eff_agent_cataloger.models import AppConfig


class FakeGitHubClient:
    def __init__(self, token: str, base_url: str | None = None) -> None:
        self.token = token
        self.base_url = base_url

    def discover_repo_names(self, org: str, keywords: list[str]) -> list[str]:
        return []

    def get_repo(self, org: str, repo_name: str):
        return {"org": org, "repo": repo_name}

    def get_repo_metadata(self, repo) -> RepoMetadata:
        repo_name = repo["repo"]
        return RepoMetadata(
            name=repo_name,
            clone_url=f"https://github.com/example-health-org/{repo_name}.git",
            default_branch="main",
            last_commit_date="2026-01-05T00:00:00+00:00",
            latest_release_tag="v0.1.0",
            latest_release_date="2026-01-10T00:00:00+00:00",
            ci_workflows=["ci.yml"],
            open_issues_count=0,
            open_pr_count=0,
        )

    def create_pull_request(
        self,
        org: str,
        repo_name: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str,
    ) -> str:
        return f"https://github.com/{org}/{repo_name}/pull/123"


def _create_mock_repo_files(local_path: Path) -> None:
    local_path.mkdir(parents=True, exist_ok=True)
    (local_path / "src").mkdir(parents=True, exist_ok=True)

    readme = """
# EHR Agent

## Overview
Agent summary.

## Quickstart
Run app.

## Installation / Setup
pip install -r requirements.txt

## Configuration
Set FHIR_BASE_URL

## Tools & Data Sources
- `fetch_fhir_patient`: read patient resource

## Examples
- Fetch patient 123

## Testing
pytest

## Safety / Compliance Notes
privacy-safe handling required.

## Repository Structure
- src/

## Changelog / Versioning
Use tags.
"""

    source = """
from toolkit import ToolRegistry
ToolRegistry.register("fetch_fhir_patient", lambda patient_id: {"id": patient_id})
FHIR_URL = "https://ehr.internal/fhir"
"""

    (local_path / "README.md").write_text(readme, encoding="utf-8")
    (local_path / "src" / "agent.py").write_text(source, encoding="utf-8")


def fake_clone_or_sync_repo(clone_url: str, local_path: Path, default_branch: str, token: str | None = None):
    _create_mock_repo_files(local_path)
    return GitSyncResult(
        success=True,
        clone_path=str(local_path),
        local_head="abc123",
        remote_head="abc123",
        synced_with_remote=True,
        last_commit_date="2026-01-06T00:00:00+00:00",
    )


def test_runner_end_to_end_dry_run_with_mocks(tmp_path, monkeypatch) -> None:
    allowed_tools_path = tmp_path / "allowed_tools.yaml"
    allowed_tools_path.write_text(
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
        org="example-health-org",
        repos=["agent-ehr"],
        agents={},
        discover=False,
        keywords=["ehr"],
        out=str(out_dir),
        clone_dir=None,
        allowed_tools_file=str(allowed_tools_path),
        apply=False,
        pr=False,
        privacy_safe_logging=True,
        token_env="GITHUB_TOKEN",
    )

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setattr(runner_module, "GitHubClient", FakeGitHubClient)
    monkeypatch.setattr(runner_module, "clone_or_sync_repo", fake_clone_or_sync_repo)

    runner = runner_module.CatalogRunner(config)
    exit_code = runner.run()

    assert exit_code == 0
    assert (out_dir / "GG_EFF_AGENT_CATALOG.md").exists()
    assert (out_dir / "GG_EFF_AGENT_CATALOG.json").exists()
    assert (out_dir / "TODO.md").exists()
    assert (out_dir / "repos" / "agent-ehr.md").exists()

    payload = json.loads((out_dir / "GG_EFF_AGENT_CATALOG.json").read_text(encoding="utf-8"))
    assert payload["repos_scanned"] == 1
    assert payload["agents"][0]["repo"] == "agent-ehr"
    assert payload["agents"][0]["tools"]["verified"][0]["tool_id"] == "fetch_fhir_patient"


def test_runner_end_to_end_apply_mode_with_pr_mock(tmp_path, monkeypatch) -> None:
    allowed_tools_path = tmp_path / "allowed_tools.yaml"
    allowed_tools_path.write_text("tools: []\n", encoding="utf-8")

    out_dir = tmp_path / "catalog"
    config = AppConfig(
        org="example-health-org",
        repos=["agent-ehr"],
        agents={},
        discover=False,
        keywords=["ehr"],
        out=str(out_dir),
        clone_dir=None,
        allowed_tools_file=str(allowed_tools_path),
        apply=True,
        pr=True,
        privacy_safe_logging=True,
        token_env="GITHUB_TOKEN",
    )

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setattr(runner_module, "GitHubClient", FakeGitHubClient)
    monkeypatch.setattr(runner_module, "clone_or_sync_repo", fake_clone_or_sync_repo)

    def fake_apply(repo_path: Path, report):
        readme = repo_path / "README.md"
        readme.write_text("# Updated README\n", encoding="utf-8")
        return [str(readme)]

    monkeypatch.setattr(runner_module, "apply_repo_updates", fake_apply)
    monkeypatch.setattr(
        runner_module,
        "create_pr_for_changes",
        lambda **kwargs: "https://github.com/example-health-org/agent-ehr/pull/456",
    )

    runner = runner_module.CatalogRunner(config)
    exit_code = runner.run()

    assert exit_code == 0

    repo_report = (out_dir / "repos" / "agent-ehr.md").read_text(encoding="utf-8")
    assert "PR: https://github.com/example-health-org/agent-ehr/pull/456" in repo_report
