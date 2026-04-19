from __future__ import annotations

import json
from pathlib import Path

from .models import CatalogReport, RepoReport


def _badge(report: RepoReport) -> str:
    if not report.repo_reachable or not report.clone_succeeded:
        return "FAIL"
    if report.required_sections_missing or report.tools.unverified:
        return "WARN"
    return "PASS"


def _tool_dump(tool_list: list) -> list[dict]:
    return [tool.model_dump(mode="json") for tool in tool_list]


def _agent_to_json(report: RepoReport) -> dict:
    return {
        "agent_name": report.agent_name,
        "repo": report.repo,
        "default_branch": report.default_branch,
        "last_commit_date": report.last_commit_date,
        "readme_status": report.readme_status.value,
        "required_sections": {
            "present": report.required_sections_present,
            "missing": report.required_sections_missing,
        },
        "tools": {
            "verified": _tool_dump(report.tools.verified),
            "unverified": _tool_dump(report.tools.unverified),
            "doc_only": _tool_dump(report.tools.doc_only),
        },
        "data_sources": [ds.model_dump(mode="json") for ds in report.data_sources],
        "issues": [issue.model_dump(mode="json") for issue in report.issues],
        "score": report.score,
    }


def write_catalog_json(catalog: CatalogReport, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / "GG_EFF_AGENT_CATALOG.json"

    payload = {
        "generated_at": catalog.generated_at.isoformat(),
        "org": catalog.org,
        "repos_scanned": catalog.repos_scanned,
        "agents": [_agent_to_json(agent) for agent in catalog.agents],
    }

    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


def write_repo_report(report: RepoReport, repo_dir: Path) -> Path:
    repo_dir.mkdir(parents=True, exist_ok=True)
    path = repo_dir / f"{report.repo}.md"

    lines: list[str] = []
    lines.append(f"# {report.agent_name} ({report.repo})")
    lines.append("")
    lines.append("## Status")
    lines.append(f"- Badge: {_badge(report)}")
    lines.append(f"- Repo reachable: {report.repo_reachable}")
    lines.append(f"- Clone/sync success: {report.clone_succeeded}")
    lines.append(f"- Synced with remote: {report.synced_with_remote}")
    lines.append(f"- Default branch: {report.default_branch or 'unknown'}")
    lines.append(f"- Last commit date: {report.last_commit_date or 'unknown'}")
    lines.append(f"- Score: {report.score}")
    lines.append("")

    lines.append("## README")
    lines.append(f"- Status: {report.readme_status.value}")
    lines.append(f"- Path: {report.readme_path or 'missing'}")
    lines.append(f"- Present sections: {', '.join(report.required_sections_present) or 'none'}")
    lines.append(f"- Missing sections: {', '.join(report.required_sections_missing) or 'none'}")
    lines.append("")

    lines.append("## Tools")
    lines.append(f"- VERIFIED: {len(report.tools.verified)}")
    for tool in report.tools.verified:
        lines.append(f"  - {tool.tool_id} ({tool.confidence.value})")
    lines.append(f"- UNVERIFIED: {len(report.tools.unverified)}")
    for tool in report.tools.unverified:
        lines.append(f"  - {tool.tool_id} ({tool.confidence.value})")
    lines.append(f"- DOC_ONLY: {len(report.tools.doc_only)}")
    for tool in report.tools.doc_only:
        lines.append(f"  - {tool.tool_id}")
    lines.append("")

    lines.append("## Data Sources")
    if not report.data_sources:
        lines.append("- none inferred")
    else:
        for source in report.data_sources:
            lines.append(
                f"- {source.name} | type={source.type} | interface={source.interface_type or 'unknown'} | confidence={source.confidence.value}"
            )
    lines.append("")

    lines.append("## CI / Release")
    lines.append(
        f"- Latest release: {report.latest_release_tag or 'none'} ({report.latest_release_date or 'n/a'})"
    )
    lines.append(f"- Workflows: {', '.join(report.ci_workflows) or 'none'}")
    lines.append("")

    lines.append("## Findings")
    if not report.issues:
        lines.append("- none")
    else:
        for issue in report.issues:
            suggestion = f" | Suggestion: {issue.suggestion}" if issue.suggestion else ""
            path_text = f" | Path: {issue.path}" if issue.path else ""
            lines.append(f"- [{issue.severity}] {issue.code}: {issue.message}{path_text}{suggestion}")

    lines.append("")
    if report.pr_url:
        lines.append(f"PR: {report.pr_url}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_catalog_markdown(catalog: CatalogReport, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / "GG_EFF_AGENT_CATALOG.md"

    lines: list[str] = []
    lines.append("# GG Eff Agent Catalog")
    lines.append("")
    lines.append(f"Generated at: {catalog.generated_at.isoformat()}")
    lines.append(f"Organization: {catalog.org}")
    lines.append(f"Repos scanned: {catalog.repos_scanned}")
    lines.append("")

    lines.append("## Agent Summary")
    lines.append("")
    lines.append("| Agent | Repo | Status | README | Unverified Tools | Score |")
    lines.append("|---|---|---|---|---:|---:|")
    for report in catalog.agents:
        lines.append(
            "| "
            f"{report.agent_name} | {report.repo} | {_badge(report)} | {report.readme_status.value} | "
            f"{len(report.tools.unverified)} | {report.score} |"
        )
    lines.append("")

    lines.append("## Per-Agent Details")
    lines.append("")
    for report in catalog.agents:
        lines.append(f"### {report.agent_name} ({report.repo})")
        lines.append(f"- Reachable: {report.repo_reachable}")
        lines.append(f"- Default branch: {report.default_branch or 'unknown'}")
        lines.append(f"- Last commit date: {report.last_commit_date or 'unknown'}")
        lines.append(f"- README: {report.readme_status.value}")
        lines.append(f"- Missing sections: {', '.join(report.required_sections_missing) or 'none'}")
        lines.append(f"- VERIFIED tools: {len(report.tools.verified)}")
        lines.append(f"- UNVERIFIED tools: {len(report.tools.unverified)}")
        lines.append(f"- DOC_ONLY tools: {len(report.tools.doc_only)}")
        lines.append(f"- Data sources inferred: {len(report.data_sources)}")
        lines.append("")

    lines.append("## Findings & Recommendations")
    lines.append("")
    findings_count = 0
    for report in catalog.agents:
        for issue in report.issues:
            findings_count += 1
            lines.append(f"- {report.repo}: [{issue.severity}] {issue.message}")
    if findings_count == 0:
        lines.append("- No major findings.")

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def write_todo(catalog: CatalogReport, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / "TODO.md"

    lines: list[str] = []
    lines.append("# GG Eff Agent Catalog TODO")
    lines.append("")

    actions = 0
    for report in catalog.agents:
        section_added = False

        if not report.repo_reachable or not report.clone_succeeded:
            lines.append(f"## {report.repo}")
            lines.append("- Resolve repository access/sync issue before documentation checks.")
            lines.append("")
            actions += 1
            continue

        if report.readme_status.value == "missing":
            if not section_added:
                lines.append(f"## {report.repo}")
                section_added = True
            actions += 1
            lines.append("- Add root README.md with required sections.")

        if report.required_sections_missing:
            if not section_added:
                lines.append(f"## {report.repo}")
                section_added = True
            actions += 1
            lines.append(
                f"- Update README with missing sections: {', '.join(report.required_sections_missing)}."
            )

        if report.tools.unverified:
            if not section_added:
                lines.append(f"## {report.repo}")
                section_added = True
            actions += 1
            unknown = ", ".join(tool.tool_id for tool in report.tools.unverified)
            lines.append(f"- Review unverified tools and add to allowlist or remove references: {unknown}.")

        manifest_missing = True
        if report.readme_path:
            manifest_path = Path(report.readme_path).parent / "agent.yaml"
            manifest_missing = not manifest_path.exists()

        if manifest_missing:
            if not section_added:
                lines.append(f"## {report.repo}")
                section_added = True
            actions += 1
            lines.append("- Add `agent.yaml` manifest (agent metadata, tool list, data sources).")

        if section_added:
            lines.append("")

    if actions == 0:
        lines.append("No actions required.")

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output
