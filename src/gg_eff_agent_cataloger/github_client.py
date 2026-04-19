from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

try:
    from github import Github
except Exception:  # pragma: no cover - fallback for environments without dependency
    Github = None  # type: ignore[assignment]


@dataclass
class RepoMetadata:
    name: str
    clone_url: str
    default_branch: str
    last_commit_date: str | None
    latest_release_tag: str | None
    latest_release_date: str | None
    ci_workflows: list[str]
    open_issues_count: int | None = None
    open_pr_count: int | None = None


def _normalize(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def discover_repo_names_from_iterable(repos: Iterable[Any], keywords: list[str]) -> list[str]:
    keyword_set = {_normalize(word) for word in keywords if word.strip()}
    if not keyword_set:
        return []

    discovered: list[str] = []
    for repo in repos:
        if getattr(repo, "archived", False):
            continue
        name = getattr(repo, "name", "")
        description = getattr(repo, "description", "") or ""
        searchable = f"{name} {description}".lower()
        normalized_searchable = _normalize(searchable)
        if any(key in normalized_searchable for key in keyword_set):
            discovered.append(name)
    return sorted(set(discovered))


class GitHubClient:
    def __init__(self, token: str, base_url: str | None = None) -> None:
        if not token:
            raise ValueError("GitHub token is required")
        if Github is None:
            raise RuntimeError("PyGithub is required but not installed")

        if base_url:
            self.client = Github(base_url=base_url, login_or_token=token)
        else:
            self.client = Github(login_or_token=token)

    def get_repo(self, org: str, repo_name: str) -> Any:
        return self.client.get_repo(f"{org}/{repo_name}")

    def list_org_repos(self, org: str) -> list[Any]:
        try:
            org_handle = self.client.get_organization(org)
            return list(org_handle.get_repos())
        except Exception:
            # Some owners are user namespaces; fall back to user repo listing.
            user_handle = self.client.get_user(org)
            return list(user_handle.get_repos())

    def discover_repo_names(self, org: str, keywords: list[str]) -> list[str]:
        repos = self.list_org_repos(org)
        return discover_repo_names_from_iterable(repos, keywords)

    def get_repo_metadata(self, repo: Any) -> RepoMetadata:
        latest_release_tag: str | None = None
        latest_release_date: str | None = None

        try:
            release = repo.get_latest_release()
            latest_release_tag = getattr(release, "tag_name", None)
            published_at = getattr(release, "published_at", None)
            if published_at:
                latest_release_date = published_at.isoformat()
        except Exception:
            latest_release_tag = None
            latest_release_date = None

        ci_workflows: list[str] = []
        try:
            workflow_entries = repo.get_contents(".github/workflows")
            if isinstance(workflow_entries, list):
                ci_workflows = [entry.name for entry in workflow_entries if getattr(entry, "type", "") == "file"]
        except Exception:
            ci_workflows = []

        pushed_at = getattr(repo, "pushed_at", None)
        last_commit_date = pushed_at.isoformat() if isinstance(pushed_at, datetime) else None

        open_pr_count: int | None = None
        try:
            open_pr_count = repo.get_pulls(state="open").totalCount
        except Exception:
            open_pr_count = None

        open_issues_count = getattr(repo, "open_issues_count", None)

        return RepoMetadata(
            name=repo.name,
            clone_url=repo.clone_url,
            default_branch=repo.default_branch,
            last_commit_date=last_commit_date,
            latest_release_tag=latest_release_tag,
            latest_release_date=latest_release_date,
            ci_workflows=ci_workflows,
            open_issues_count=open_issues_count,
            open_pr_count=open_pr_count,
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
        repo = self.get_repo(org, repo_name)
        pull = repo.create_pull(
            title=title,
            body=body,
            head=head_branch,
            base=base_branch,
            maintainer_can_modify=True,
        )
        return pull.html_url

