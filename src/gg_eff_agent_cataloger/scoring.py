from __future__ import annotations

from .models import ReadmeStatus, RepoReport


def compute_repo_score(report: RepoReport) -> int:
    score = 100

    if not report.repo_reachable:
        return 0

    if not report.clone_succeeded:
        score -= 30
    if not report.synced_with_remote:
        score -= 20

    if report.readme_status == ReadmeStatus.MISSING:
        score -= 25
    elif report.readme_status == ReadmeStatus.NEEDS_UPDATE:
        score -= 10

    missing_sections_penalty = min(30, len(report.required_sections_missing) * 5)
    score -= missing_sections_penalty

    if "Tools & Data Sources" in report.required_sections_missing:
        score -= 15

    score -= min(15, len(report.tools.unverified) * 3)
    score -= min(10, len(report.tools.doc_only) * 2)

    return max(0, min(100, score))
