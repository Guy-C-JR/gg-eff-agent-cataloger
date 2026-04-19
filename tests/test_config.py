import argparse

from gg_eff_agent_cataloger.config import build_config


def test_build_config_defaults_to_dry_run() -> None:
    args = argparse.Namespace(
        org="example-health-org",
        repos="agent-ehr",
        discover=None,
        keywords=None,
        config_file=None,
        allowed_tools_file=None,
        out="catalog",
        clone_dir=None,
        local_repos_dir=None,
        apply=None,
        pr=True,
        privacy_safe_logging=None,
        token_env=None,
        github_base_url=None,
    )

    config = build_config(args)

    assert config.apply is False
    assert config.pr is False


def test_build_config_local_mode_sets_default_org() -> None:
    args = argparse.Namespace(
        org=None,
        repos="ehr-ai-agent",
        discover=None,
        keywords=None,
        config_file=None,
        allowed_tools_file=None,
        out="catalog",
        clone_dir=None,
        local_repos_dir="./sample-agent-repos",
        apply=None,
        pr=None,
        privacy_safe_logging=None,
        token_env=None,
        github_base_url=None,
    )

    config = build_config(args)

    assert config.org == "local"
    assert config.local_repos_dir == "./sample-agent-repos"
