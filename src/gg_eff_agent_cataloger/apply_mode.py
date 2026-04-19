from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from .models import RepoReport
from .readme_analysis import find_root_readme

try:
    from git import Repo
except Exception:  # pragma: no cover - fallback for environments without dependency
    Repo = None  # type: ignore[assignment]


def _all_tools(report: RepoReport):
    return report.tools.verified + report.tools.unverified + report.tools.doc_only


def render_readme_template(report: RepoReport) -> str:
    tool_lines: list[str] = []
    for tool in _all_tools(report):
        status = tool.status.value
        ds_text = ", ".join(ds.name for ds in tool.data_sources) or "TODO"
        tool_lines.append(f"- `{tool.tool_id}` ({status})")
        tool_lines.append(f"  - Purpose: {tool.purpose or 'TODO'}")
        tool_lines.append(f"  - Inputs/Outputs: {tool.inputs or 'TODO'} / {tool.outputs or 'TODO'}")
        tool_lines.append(f"  - Data Sources: {ds_text}")
        tool_lines.append(
            f"  - Permissions: {', '.join(tool.permissions) if tool.permissions else 'TODO'}"
        )

    if not tool_lines:
        tool_lines = ["- TODO: Add tool list, purpose, I/O, data sources, and permissions."]

    return "\n".join(
        [
            f"# {report.agent_name} Agent",
            "",
            "## Overview",
            "TODO: Describe what the agent does and the problem it solves.",
            "",
            "## Quickstart",
            "TODO: Provide minimal steps to run the agent.",
            "",
            "## Installation / Setup",
            "TODO: Document dependencies and environment variables (without secrets).",
            "",
            "## Configuration",
            "TODO: Describe config files and required parameters.",
            "",
            "## Tools & Data Sources",
            *tool_lines,
            "",
            "## Examples",
            "TODO: Add 1-3 example invocations or prompts.",
            "",
            "## Testing",
            "TODO: Describe tests and lint commands.",
            "",
            "## Safety / Compliance Notes",
            "TODO: Document privacy handling expectations and guardrails.",
            "",
            "## Repository Structure",
            "TODO: Describe key folders/files.",
            "",
            "## Changelog / Versioning",
            "TODO: Link releases/tags or maintain lightweight changelog notes.",
            "",
        ]
    )


def append_missing_sections(existing: str, missing_sections: list[str]) -> str:
    lines = [existing.rstrip(), "", "## Documentation Gaps (auto-added)"]
    for section in missing_sections:
        lines.append("")
        lines.append(f"## {section}")
        lines.append("TODO: Complete this section.")
    lines.append("")
    return "\n".join(lines)


def build_agent_manifest(report: RepoReport) -> str:
    data = {
        "agent_id": report.repo,
        "agent_name": report.agent_name,
        "description": f"{report.agent_name} agent",
        "entrypoint": "TODO",
        "tools": [],
        "data_sources": [],
    }

    for tool in _all_tools(report):
        data["tools"].append(
            {
                "tool_id": tool.tool_id,
                "tool_name": tool.tool_name,
                "purpose": tool.purpose or "TODO",
                "data_sources": [
                    {
                        "name": source.name,
                        "type": source.type,
                        "environment": source.environment or "unknown",
                    }
                    for source in tool.data_sources
                ],
                "permissions": ",".join(tool.permissions) if tool.permissions else "read",
            }
        )

    for source in report.data_sources:
        data["data_sources"].append(
            {
                "name": source.name,
                "type": source.type,
                "environment": source.environment or "unknown",
                "owner": source.owner or "TODO",
                "notes": source.notes or "",
            }
        )

    return yaml.safe_dump(data, sort_keys=False)


def apply_repo_updates(repo_path: Path, report: RepoReport) -> list[str]:
    changed_files: list[str] = []

    readme_path = find_root_readme(repo_path)
    if readme_path is None:
        readme_path = repo_path / "README.md"
        readme_path.write_text(render_readme_template(report), encoding="utf-8")
        changed_files.append(str(readme_path))
    elif report.required_sections_missing:
        content = readme_path.read_text(encoding="utf-8", errors="ignore")
        updated = append_missing_sections(content, report.required_sections_missing)
        if updated != content:
            readme_path.write_text(updated, encoding="utf-8")
            changed_files.append(str(readme_path))

    manifest_path = repo_path / "agent.yaml"
    if not manifest_path.exists():
        manifest_path.write_text(build_agent_manifest(report), encoding="utf-8")
        changed_files.append(str(manifest_path))

    return changed_files


def create_pr_for_changes(
    repo_path: Path,
    repo_name: str,
    org: str,
    default_branch: str,
    changed_files: list[str],
    github_client,
) -> str | None:
    if not changed_files:
        return None

    if Repo is None:
        raise RuntimeError("GitPython is required but not installed")

    repo = Repo(repo_path)
    branch_name = f"codex/docs-{repo_name}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    repo.git.checkout(default_branch)
    repo.git.checkout("-B", branch_name)

    rel_paths = [str(Path(path).relative_to(repo_path)) for path in changed_files]
    repo.index.add(rel_paths)

    if not repo.is_dirty(index=True, working_tree=True, untracked_files=True):
        return None

    repo.index.commit(f"docs: add/update README for {repo_name}")
    repo.remote("origin").push(refspec=f"{branch_name}:{branch_name}")

    return github_client.create_pull_request(
        org=org,
        repo_name=repo_name,
        title=f"docs: add/update README for {repo_name}",
        body="Automated README/manifest update generated by gg_eff_agent_cataloger.",
        head_branch=branch_name,
        base_branch=default_branch,
    )
