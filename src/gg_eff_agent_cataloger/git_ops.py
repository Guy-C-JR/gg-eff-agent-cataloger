from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

try:
    from git import Repo
except Exception:  # pragma: no cover - fallback for environments without dependency
    Repo = None  # type: ignore[assignment]


class GitSyncResult:
    def __init__(
        self,
        success: bool,
        clone_path: str,
        local_head: str | None,
        remote_head: str | None,
        synced_with_remote: bool,
        last_commit_date: str | None,
        error: str | None = None,
    ) -> None:
        self.success = success
        self.clone_path = clone_path
        self.local_head = local_head
        self.remote_head = remote_head
        self.synced_with_remote = synced_with_remote
        self.last_commit_date = last_commit_date
        self.error = error


def _inject_token(clone_url: str, token: str | None) -> str:
    if not token:
        return clone_url

    parsed = urlparse(clone_url)
    if parsed.scheme not in {"http", "https"}:
        return clone_url

    netloc = f"x-access-token:{token}@{parsed.netloc}"
    return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))


def _sanitize_error(error: str, token: str | None) -> str:
    sanitized = error
    if token:
        sanitized = sanitized.replace(token, "***")
    sanitized = sanitized.replace("x-access-token:", "x-access-token:[REDACTED]")
    return sanitized


def clone_or_sync_repo(
    clone_url: str,
    local_path: Path,
    default_branch: str,
    token: str | None = None,
) -> GitSyncResult:
    if Repo is None:
        return GitSyncResult(
            success=False,
            clone_path=str(local_path),
            local_head=None,
            remote_head=None,
            synced_with_remote=False,
            last_commit_date=None,
            error="GitPython is required but not installed",
        )

    local_path.parent.mkdir(parents=True, exist_ok=True)
    auth_url = _inject_token(clone_url, token)

    try:
        if (local_path / ".git").exists():
            repo = Repo(local_path)
            origin = repo.remotes.origin
            origin.fetch()
        else:
            repo = Repo.clone_from(auth_url, str(local_path))
            origin = repo.remotes.origin

        origin.fetch(default_branch)
        repo.git.checkout(default_branch)
        repo.git.reset("--hard", f"origin/{default_branch}")

        local_head = repo.head.commit.hexsha
        remote_head = repo.commit(f"origin/{default_branch}").hexsha
        synced_with_remote = local_head == remote_head

        commit_dt = datetime.fromtimestamp(repo.head.commit.committed_date, tz=timezone.utc)
        last_commit_date = commit_dt.isoformat()

        return GitSyncResult(
            success=True,
            clone_path=str(local_path),
            local_head=local_head,
            remote_head=remote_head,
            synced_with_remote=synced_with_remote,
            last_commit_date=last_commit_date,
        )
    except Exception as exc:
        return GitSyncResult(
            success=False,
            clone_path=str(local_path),
            local_head=None,
            remote_head=None,
            synced_with_remote=False,
            last_commit_date=None,
            error=_sanitize_error(str(exc), token),
        )
