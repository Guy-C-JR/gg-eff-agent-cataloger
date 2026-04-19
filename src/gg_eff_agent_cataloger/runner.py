from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from .apply_mode import apply_repo_updates, create_pr_for_changes
from .config import guess_agent_name, resolve_repo_targets
from .git_ops import clone_or_sync_repo
from .github_client import GitHubClient
from .logging_utils import SafeLogger
from .models import (
    AllowedTool,
    CatalogReport,
    ReadmeStatus,
    RepoIssue,
    RepoReport,
    RunSummary,
    ToolBuckets,
)
from .readme_analysis import analyze_readme, extract_documented_tools, find_broken_local_links
from .reporting import write_catalog_json, write_catalog_markdown, write_repo_report, write_todo
from .scoring import compute_repo_score
from .tool_inference import infer_tools_and_data_sources, load_allowed_tools

try:
    from git import Repo
except Exception:  # pragma: no cover - fallback for environments without dependency
    Repo = None  # type: ignore[assignment]


class CatalogRunner:
    CONTENT_ANALYSIS_ISSUE_CODES = {
        "README_MISSING",
        "README_SECTIONS_MISSING",
        "README_BROKEN_LOCAL_LINKS",
        "TOOL_UNVERIFIED",
        "TOOLS_DATA_SOURCES_SECTION_MISSING",
    }

    def __init__(self, config) -> None:
        self.config = config
        self.logger = SafeLogger(privacy_safe_logging=config.privacy_safe_logging)

    def run(self) -> int:
        local_mode = bool(self.config.local_repos_dir)

        token: str | None = None
        github_client: GitHubClient | None = None

        if local_mode:
            self.logger.info("Running in LOCAL mode (--local-repos-dir)")
        else:
            token = os.getenv(self.config.token_env)
            if not token:
                self.logger.error(
                    f"Missing GitHub token in environment variable '{self.config.token_env}'."
                )
                return 2

        out_dir = Path(self.config.out)
        clone_base = Path(self.config.clone_dir) if self.config.clone_dir else out_dir / "_clones"
        repo_report_dir = out_dir / "repos"
        out_dir.mkdir(parents=True, exist_ok=True)
        repo_report_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info("Starting AI agent catalog scan")
        self.logger.info(f"Mode: {'APPLY' if self.config.apply else 'DRY-RUN'}")

        local_base: Path | None = None
        if local_mode:
            local_base = Path(self.config.local_repos_dir)
            if not local_base.exists() or not local_base.is_dir():
                self.logger.error(f"Local repos directory not found: {local_base}")
                return 2
            if self.config.clone_dir:
                self.logger.warn("--clone-dir is ignored in local mode")
            if self.config.pr:
                self.logger.warn("--pr is ignored in local mode (no remote PR creation)")
        else:
            try:
                github_client = GitHubClient(token=token or "", base_url=self.config.github_base_url)
            except Exception as exc:
                self.logger.error(f"Failed to initialize GitHub client: {exc}")
                return 2

        allowed_tools = load_allowed_tools(Path(self.config.allowed_tools_file))
        self.logger.safe_detail(f"Allowlist tools loaded: {len(allowed_tools)}")

        targets = resolve_repo_targets(self.config)
        if self.config.discover:
            existing = {repo for _, repo in targets}
            if local_mode:
                discovered = self._discover_local_repo_names(local_base or Path("."), self.config.keywords)
            else:
                try:
                    if github_client is None:
                        raise RuntimeError("GitHub client not initialized")
                    discovered = github_client.discover_repo_names(
                        self.config.org,
                        self.config.keywords,
                    )
                except Exception as exc:
                    self.logger.error(
                        f"Repository discovery failed for org '{self.config.org}': {exc}"
                    )
                    return 4

            for repo_name in discovered:
                if repo_name in existing:
                    continue
                targets.append((guess_agent_name(repo_name), repo_name))
                existing.add(repo_name)

        if not targets:
            self.logger.warn("No repositories to scan. Use --repos, --discover, or config mapping.")
            return 3

        reports: list[RepoReport] = []

        for agent_name, repo_name in targets:
            self.logger.info(f"Scanning repo: {repo_name}")

            if local_mode:
                report = self._scan_single_repo_local(
                    local_base=local_base or Path("."),
                    agent_name=agent_name,
                    repo_name=repo_name,
                    allowed_tools=allowed_tools,
                )
            else:
                report = self._scan_single_repo_remote(
                    github_client=github_client,
                    token=token or "",
                    clone_base=clone_base,
                    agent_name=agent_name,
                    repo_name=repo_name,
                    allowed_tools=allowed_tools,
                )

            write_repo_report(report, repo_report_dir)
            reports.append(report)

        catalog = CatalogReport(
            generated_at=datetime.now(timezone.utc),
            org=self.config.org,
            repos_scanned=len(reports),
            agents=reports,
        )

        write_catalog_json(catalog, out_dir)
        write_catalog_markdown(catalog, out_dir)
        write_todo(catalog, out_dir)

        summary = self._build_summary(reports)
        self._print_summary(summary)

        if any(not report.repo_reachable or not report.clone_succeeded for report in reports):
            return 1

        return 0

    def _normalize_local_repo_folder_name(self, folder_name: str) -> str:
        lowered = folder_name.lower()
        if lowered.endswith("-main"):
            return folder_name[:-5]
        if lowered.endswith("-master"):
            return folder_name[:-7]
        return folder_name

    def _discover_local_repo_names(self, local_base: Path, keywords: list[str]) -> list[str]:
        keyword_set = {keyword.lower() for keyword in keywords if keyword.strip()}
        discovered: list[str] = []

        for child in local_base.iterdir():
            if not child.is_dir():
                continue
            canonical_name = self._normalize_local_repo_folder_name(child.name)
            searchable = canonical_name.lower()
            if not keyword_set or any(keyword in searchable for keyword in keyword_set):
                discovered.append(canonical_name)

        return sorted(set(discovered))

    def _resolve_local_repo_path(self, local_base: Path, repo_name: str) -> tuple[Path | None, str | None]:
        candidates = [repo_name, f"{repo_name}-main", f"{repo_name}-master"]
        for candidate in candidates:
            candidate_path = local_base / candidate
            if candidate_path.exists() and candidate_path.is_dir():
                return candidate_path, candidate
        return None, None

    def _scan_single_repo_remote(
        self,
        github_client: GitHubClient | None,
        token: str,
        clone_base: Path,
        agent_name: str,
        repo_name: str,
        allowed_tools: list[AllowedTool],
    ) -> RepoReport:
        report = RepoReport(agent_name=agent_name, repo=repo_name)

        if github_client is None:
            report.issues.append(
                RepoIssue(
                    code="GITHUB_CLIENT_NOT_INITIALIZED",
                    severity="critical",
                    message="GitHub client not initialized for remote mode.",
                    suggestion="Check token configuration and rerun.",
                )
            )
            report.score = compute_repo_score(report)
            return report

        try:
            repo = github_client.get_repo(self.config.org, repo_name)
            report.repo_reachable = True
        except Exception as exc:
            report.issues.append(
                RepoIssue(
                    code="REPO_UNREACHABLE",
                    severity="critical",
                    message=f"Repository not reachable: {exc}",
                    suggestion="Verify repository name, org, and token permissions.",
                )
            )
            report.score = compute_repo_score(report)
            return report

        metadata = github_client.get_repo_metadata(repo)
        report.default_branch = metadata.default_branch
        report.latest_release_tag = metadata.latest_release_tag
        report.latest_release_date = metadata.latest_release_date
        report.ci_workflows = metadata.ci_workflows

        clone_path = clone_base / repo_name
        sync_result = clone_or_sync_repo(
            clone_url=metadata.clone_url,
            local_path=clone_path,
            default_branch=metadata.default_branch,
            token=token,
        )

        report.clone_succeeded = sync_result.success
        report.synced_with_remote = sync_result.synced_with_remote
        report.local_head = sync_result.local_head
        report.remote_head = sync_result.remote_head
        report.last_commit_date = sync_result.last_commit_date or metadata.last_commit_date

        if not sync_result.success:
            report.issues.append(
                RepoIssue(
                    code="SYNC_FAILED",
                    severity="high",
                    message=f"Clone/fetch failed: {sync_result.error}",
                    suggestion="Ensure default branch is reachable and git credentials are valid.",
                )
            )
            report.score = compute_repo_score(report)
            return report

        self._analyze_repo_contents(report, clone_path, allowed_tools)

        if self.config.apply:
            self._apply_changes(
                report=report,
                repo_path=clone_path,
                repo_name=repo_name,
                default_branch=metadata.default_branch,
                github_client=github_client,
            )
            self._reanalyze_after_apply_if_changed(report, clone_path, allowed_tools)

        report.score = compute_repo_score(report)
        return report

    def _scan_single_repo_local(
        self,
        local_base: Path,
        agent_name: str,
        repo_name: str,
        allowed_tools: list[AllowedTool],
    ) -> RepoReport:
        report = RepoReport(agent_name=agent_name, repo=repo_name)
        repo_path, matched_dir_name = self._resolve_local_repo_path(local_base, repo_name)

        if repo_path is None:
            report.issues.append(
                RepoIssue(
                    code="LOCAL_REPO_NOT_FOUND",
                    severity="critical",
                    message=f"Local repository directory not found for '{repo_name}' in {local_base}",
                    suggestion="Clone/download the repository into --local-repos-dir.",
                )
            )
            report.score = compute_repo_score(report)
            return report

        if matched_dir_name and matched_dir_name != repo_name:
            report.issues.append(
                RepoIssue(
                    code="LOCAL_REPO_DIR_ALIAS",
                    severity="low",
                    message=(
                        f"Using local directory '{matched_dir_name}' for requested repo '{repo_name}'."
                    ),
                    suggestion="Rename local folder to canonical repo name to reduce ambiguity.",
                )
            )

        report.repo_reachable = True
        report.clone_succeeded = True
        report.synced_with_remote = True

        workflows_path = repo_path / ".github" / "workflows"
        if workflows_path.exists() and workflows_path.is_dir():
            report.ci_workflows = sorted(
                [entry.name for entry in workflows_path.iterdir() if entry.is_file()]
            )

        if Repo is not None and (repo_path / ".git").exists():
            try:
                repo = Repo(repo_path)

                try:
                    report.default_branch = repo.active_branch.name
                except Exception:
                    report.default_branch = "unknown"

                head_commit = repo.head.commit
                report.local_head = head_commit.hexsha
                report.last_commit_date = datetime.fromtimestamp(
                    head_commit.committed_date,
                    tz=timezone.utc,
                ).isoformat()

                if report.default_branch and report.default_branch != "unknown":
                    ref_name = f"origin/{report.default_branch}"
                    ref_map = {ref.name: ref for ref in repo.refs}
                    if ref_name in ref_map:
                        remote_commit = repo.commit(ref_name)
                        report.remote_head = remote_commit.hexsha
                        report.synced_with_remote = report.local_head == report.remote_head
                    else:
                        report.issues.append(
                            RepoIssue(
                                code="CURRENCY_NOT_VERIFIED",
                                severity="medium",
                                message="Remote default branch state not available locally.",
                                suggestion="Run `git fetch origin` or run in remote mode to verify up-to-date status.",
                            )
                        )

                if repo.tags:
                    latest_tag = max(repo.tags, key=lambda tag: tag.commit.committed_date)
                    report.latest_release_tag = latest_tag.name
                    report.latest_release_date = datetime.fromtimestamp(
                        latest_tag.commit.committed_date,
                        tz=timezone.utc,
                    ).isoformat()
            except Exception as exc:
                report.issues.append(
                    RepoIssue(
                        code="LOCAL_GIT_METADATA_FAILED",
                        severity="low",
                        message=f"Failed to inspect local git metadata: {exc}",
                        suggestion="Ensure the local folder is a valid git repository.",
                    )
                )
        else:
            report.issues.append(
                RepoIssue(
                    code="CURRENCY_NOT_VERIFIED",
                    severity="medium",
                    message="Local repository is not a git clone (or GitPython unavailable).",
                    suggestion="Use a full git clone to verify branch currency.",
                )
            )

        self._analyze_repo_contents(report, repo_path, allowed_tools)

        if self.config.apply:
            self._apply_changes(
                report=report,
                repo_path=repo_path,
                repo_name=repo_name,
                default_branch=report.default_branch or "main",
                github_client=None,
            )
            self._reanalyze_after_apply_if_changed(report, repo_path, allowed_tools)

        report.score = compute_repo_score(report)
        return report

    def _reset_content_analysis_fields(self, report: RepoReport) -> None:
        report.readme_status = ReadmeStatus.MISSING
        report.readme_path = None
        report.required_sections_present = []
        report.required_sections_missing = []
        report.tools = ToolBuckets()
        report.data_sources = []
        report.issues = [
            issue
            for issue in report.issues
            if issue.code not in self.CONTENT_ANALYSIS_ISSUE_CODES
        ]

    def _reanalyze_after_apply_if_changed(
        self,
        report: RepoReport,
        repo_path: Path,
        allowed_tools: list[AllowedTool],
    ) -> None:
        if not report.apply_changes:
            return

        self._reset_content_analysis_fields(report)
        self._analyze_repo_contents(report, repo_path, allowed_tools)

    def _analyze_repo_contents(
        self,
        report: RepoReport,
        repo_path: Path,
        allowed_tools: list[AllowedTool],
    ) -> None:
        readme = analyze_readme(repo_path)
        report.readme_status = readme.status
        report.readme_path = readme.path
        report.required_sections_present = readme.present_sections
        report.required_sections_missing = readme.missing_sections

        if readme.status.value == "missing":
            report.issues.append(
                RepoIssue(
                    code="README_MISSING",
                    severity="high",
                    message="README missing at repository root.",
                    suggestion="Add README.md with required sections.",
                )
            )

        if readme.missing_sections:
            report.issues.append(
                RepoIssue(
                    code="README_SECTIONS_MISSING",
                    severity="medium",
                    message=f"README missing sections: {', '.join(readme.missing_sections)}",
                    suggestion="Fill required sections using the standard template.",
                    path=readme.path,
                )
            )

        if readme.content:
            broken_links = find_broken_local_links(repo_path, readme.content)
            if broken_links:
                report.issues.append(
                    RepoIssue(
                        code="README_BROKEN_LOCAL_LINKS",
                        severity="low",
                        message=f"README has broken local links ({len(broken_links)}).",
                        suggestion="Fix or remove broken links.",
                        path=readme.path,
                    )
                )

        documented_tools = extract_documented_tools(readme.content)
        tool_buckets, data_sources = infer_tools_and_data_sources(
            repo_path=repo_path,
            readme_tools=documented_tools,
            allowed_tools=allowed_tools,
        )

        report.tools = tool_buckets
        report.data_sources = data_sources

        for tool in report.tools.unverified:
            report.issues.append(
                RepoIssue(
                    code="TOOL_UNVERIFIED",
                    severity="medium",
                    message=f"Unverified tool: {tool.tool_id}",
                    suggestion="Add tool to allowlist or remove unsupported tool usage.",
                )
            )

        if "Tools & Data Sources" in report.required_sections_missing:
            report.issues.append(
                RepoIssue(
                    code="TOOLS_DATA_SOURCES_SECTION_MISSING",
                    severity="high",
                    message="README missing critical 'Tools & Data Sources' section.",
                    suggestion="Add tool inventory with purpose, I/O, data sources, and permissions.",
                    path=readme.path,
                )
            )

    def _apply_changes(
        self,
        report: RepoReport,
        repo_path: Path,
        repo_name: str,
        default_branch: str,
        github_client: GitHubClient | None,
    ) -> None:
        changes = apply_repo_updates(repo_path, report)
        report.apply_changes = changes

        if not changes or not self.config.pr:
            return

        if github_client is None:
            report.issues.append(
                RepoIssue(
                    code="PR_CREATION_SKIPPED_LOCAL",
                    severity="medium",
                    message="PR creation skipped in local mode.",
                    suggestion="Run in remote mode with token access to open PRs automatically.",
                )
            )
            return

        try:
            pr_url = create_pr_for_changes(
                repo_path=repo_path,
                repo_name=repo_name,
                org=self.config.org,
                default_branch=default_branch,
                changed_files=changes,
                github_client=github_client,
            )
            report.pr_url = pr_url
        except Exception as exc:
            report.issues.append(
                RepoIssue(
                    code="PR_CREATION_FAILED",
                    severity="high",
                    message=f"Failed to create PR: {exc}",
                    suggestion="Check branch push permissions and token scope.",
                )
            )

    def _build_summary(self, reports: list[RepoReport]) -> RunSummary:
        reachable_reports = [
            report for report in reports if report.repo_reachable and report.clone_succeeded
        ]

        missing_readme_count = sum(
            1 for report in reachable_reports if report.readme_status.value == "missing"
        )
        missing_tools_section_count = sum(
            1
            for report in reachable_reports
            if "Tools & Data Sources" in report.required_sections_missing
        )
        unverified_tool_count = sum(len(report.tools.unverified) for report in reachable_reports)

        passed_required = sum(
            1
            for report in reachable_reports
            if report.readme_status.value == "ok" and not report.required_sections_missing
        )

        return RunSummary(
            repos_scanned=len(reports),
            repos_passed_required_checks=passed_required,
            repos_failed_required_checks=len(reports) - passed_required,
            missing_readme_count=missing_readme_count,
            missing_tools_data_sources_section_count=missing_tools_section_count,
            unverified_tool_count=unverified_tool_count,
        )

    def _print_summary(self, summary: RunSummary) -> None:
        self.logger.success("Scan complete")
        self.logger.safe_detail(f"Repos scanned: {summary.repos_scanned}")
        self.logger.safe_detail(f"Passed required checks: {summary.repos_passed_required_checks}")
        self.logger.safe_detail(f"Failed required checks: {summary.repos_failed_required_checks}")
        self.logger.safe_detail(f"Missing README count: {summary.missing_readme_count}")
        self.logger.safe_detail(
            "Missing 'Tools & Data Sources' section count: "
            f"{summary.missing_tools_data_sources_section_count}"
        )
        self.logger.safe_detail(f"Unverified tools count: {summary.unverified_tool_count}")





