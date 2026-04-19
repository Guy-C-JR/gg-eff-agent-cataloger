from gg_eff_agent_cataloger.apply_mode import append_missing_sections, build_agent_manifest
from gg_eff_agent_cataloger.models import RepoReport


def test_append_missing_sections() -> None:
    original = "# Agent\n\n## Overview\nBody"
    updated = append_missing_sections(original, ["Quickstart", "Testing"])

    assert "## Quickstart" in updated
    assert "## Testing" in updated


def test_build_agent_manifest_contains_minimum_keys() -> None:
    report = RepoReport(agent_name="EHR", repo="agent-ehr")
    manifest = build_agent_manifest(report)

    assert "agent_id: agent-ehr" in manifest
    assert "agent_name: EHR" in manifest
    assert "tools:" in manifest
    assert "data_sources:" in manifest
