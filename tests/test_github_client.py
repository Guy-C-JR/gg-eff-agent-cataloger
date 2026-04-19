from dataclasses import dataclass

from gg_eff_agent_cataloger.github_client import discover_repo_names_from_iterable


@dataclass
class FakeRepo:
    name: str
    description: str
    archived: bool = False


def test_discovery_filters_archived_and_matches_keywords() -> None:
    repos = [
        FakeRepo(name="agent-ehr", description="EHR agent"),
        FakeRepo(name="service-gwas", description="GWAS analysis agent"),
        FakeRepo(name="archived-agent-rx", description="rx agent", archived=True),
        FakeRepo(name="misc-tools", description="not relevant"),
    ]

    discovered = discover_repo_names_from_iterable(repos, ["ehr", "gwas", "rx"])

    assert "agent-ehr" in discovered
    assert "service-gwas" in discovered
    assert "archived-agent-rx" not in discovered
    assert "misc-tools" not in discovered
