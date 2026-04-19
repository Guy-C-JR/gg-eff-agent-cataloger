from pathlib import Path

from gg_eff_agent_cataloger.tool_inference import infer_tools_and_data_sources, load_allowed_tools


def test_inference_detects_verified_unverified_and_doc_only_tools() -> None:
    repo_path = Path("tests/fixtures/sample_agent_repo")
    allowed_tools = load_allowed_tools(Path("config/allowed_tools.yaml"))

    readme_tools = ["fetch_fhir_patient", "debug_scratch_tool"]
    buckets, data_sources = infer_tools_and_data_sources(
        repo_path=repo_path,
        readme_tools=readme_tools,
        allowed_tools=allowed_tools,
    )

    verified_ids = {tool.tool_id for tool in buckets.verified}
    unverified_ids = {tool.tool_id for tool in buckets.unverified}
    doc_only_ids = {tool.tool_id for tool in buckets.doc_only}

    assert "fetch_fhir_patient" in verified_ids
    assert "unknown_debug_tool" in unverified_ids
    assert "debug_scratch_tool" in doc_only_ids

    data_source_names = {source.name for source in data_sources}
    assert "FHIR API" in data_source_names
    assert "Snowflake" in data_source_names
    assert "Amazon S3" in data_source_names


def test_inference_ignores_http_endpoint_like_tool_identifiers(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir(parents=True, exist_ok=True)

    (repo_path / "agent.yaml").write_text(
        """
agent_id: test-agent
agent_name: Test
entrypoint: python -m app
tools:
  - tool_id: "**POST /process**"
    tool_name: "**POST /process**"
    purpose: endpoint descriptor
    data_sources: []
    permissions: [read]
  - tool_id: query_ehr_db
    tool_name: QueryEHRDatabase
    purpose: query helper
    data_sources: []
    permissions: [read]

data_sources: []
""".strip()
        + "\n",
        encoding="utf-8",
    )

    allowed_tools = load_allowed_tools(Path("config/allowed_tools.yaml"))
    buckets, _ = infer_tools_and_data_sources(
        repo_path=repo_path,
        readme_tools=["**POST /process**"],
        allowed_tools=allowed_tools,
    )

    all_ids = {tool.tool_id for tool in buckets.verified + buckets.unverified + buckets.doc_only}
    assert "**POST /process**" not in all_ids
    assert "POST /process" not in all_ids
    assert "query_ehr_db" in {tool.tool_id for tool in buckets.verified}
