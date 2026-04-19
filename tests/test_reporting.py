from datetime import datetime, timezone

from gg_eff_agent_cataloger.models import CatalogReport, RepoReport
from gg_eff_agent_cataloger.reporting import write_catalog_json, write_catalog_markdown, write_repo_report, write_todo


def test_reporting_writes_expected_files(tmp_path) -> None:
    report = RepoReport(agent_name="EHR", repo="agent-ehr", repo_reachable=True, clone_succeeded=True)
    catalog = CatalogReport(
        generated_at=datetime.now(timezone.utc),
        org="example-health-org",
        repos_scanned=1,
        agents=[report],
    )

    repo_path = write_repo_report(report, tmp_path / "repos")
    json_path = write_catalog_json(catalog, tmp_path)
    md_path = write_catalog_markdown(catalog, tmp_path)
    todo_path = write_todo(catalog, tmp_path)

    assert repo_path.exists()
    assert json_path.exists()
    assert md_path.exists()
    assert todo_path.exists()

    assert "agent-ehr" in md_path.read_text(encoding="utf-8")


def test_todo_for_unreachable_repo_is_access_action(tmp_path) -> None:
    report = RepoReport(agent_name="EHR", repo="agent-ehr", repo_reachable=False, clone_succeeded=False)
    catalog = CatalogReport(
        generated_at=datetime.now(timezone.utc),
        org="example-health-org",
        repos_scanned=1,
        agents=[report],
    )

    todo_path = write_todo(catalog, tmp_path)
    todo_text = todo_path.read_text(encoding="utf-8")
    assert "Resolve repository access/sync issue" in todo_text
    assert "Add root README.md" not in todo_text
