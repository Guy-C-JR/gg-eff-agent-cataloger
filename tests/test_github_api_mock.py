from dataclasses import dataclass
from datetime import datetime, timezone

import gg_eff_agent_cataloger.github_client as github_client_module


@dataclass
class FakeRepoRef:
    name: str
    description: str
    archived: bool = False


class FakeRelease:
    tag_name = "v1.2.3"
    published_at = datetime(2025, 1, 1, tzinfo=timezone.utc)


class FakeWorkflowEntry:
    def __init__(self, name: str) -> None:
        self.name = name
        self.type = "file"


class FakePulls:
    totalCount = 7


class FakeRepo:
    name = "agent-ehr"
    clone_url = "https://github.com/example-health-org/agent-ehr.git"
    default_branch = "main"
    pushed_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    open_issues_count = 4

    def get_latest_release(self):
        return FakeRelease()

    def get_contents(self, path: str):
        assert path == ".github/workflows"
        return [FakeWorkflowEntry("ci.yml")]

    def get_pulls(self, state: str):
        assert state == "open"
        return FakePulls()


class FakeOrg:
    def get_repos(self):
        return [
            FakeRepoRef("agent-ehr", "EHR agent"),
            FakeRepoRef("misc", "not related"),
        ]


class FakeUser:
    def get_repos(self):
        return [
            FakeRepoRef("agent-pgx", "PGX agent"),
        ]


class FakeGithub:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def get_repo(self, full_name: str):
        assert full_name == "example-health-org/agent-ehr"
        return FakeRepo()

    def get_organization(self, org_name: str):
        assert org_name == "example-health-org"
        return FakeOrg()


class FakeGithubUserFallback(FakeGithub):
    def get_organization(self, org_name: str):
        raise RuntimeError("org not found")

    def get_user(self, user_name: str):
        assert user_name == "example-health-org"
        return FakeUser()


def test_github_client_mocked_api(monkeypatch) -> None:
    monkeypatch.setattr(github_client_module, "Github", FakeGithub)

    client = github_client_module.GitHubClient(token="token")
    repo = client.get_repo("example-health-org", "agent-ehr")
    meta = client.get_repo_metadata(repo)
    discovered = client.discover_repo_names("example-health-org", ["ehr"])

    assert meta.default_branch == "main"
    assert meta.latest_release_tag == "v1.2.3"
    assert meta.ci_workflows == ["ci.yml"]
    assert discovered == ["agent-ehr"]


def test_github_client_owner_user_fallback(monkeypatch) -> None:
    monkeypatch.setattr(github_client_module, "Github", FakeGithubUserFallback)

    client = github_client_module.GitHubClient(token="token")
    discovered = client.discover_repo_names("example-health-org", ["pgx"])

    assert discovered == ["agent-pgx"]
