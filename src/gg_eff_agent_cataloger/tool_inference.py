from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .constants import CODE_FILE_EXTENSIONS, CONFIG_LIKE_EXTENSIONS, SCAN_IGNORE_DIRS
from .models import (
    AllowedTool,
    ConfidenceLevel,
    DataSourceRecord,
    ToolBuckets,
    ToolRecord,
    ToolVerificationStatus,
)


TOOL_REGEX_PATTERNS: list[tuple[re.Pattern[str], ConfidenceLevel]] = [
    (re.compile(r"ToolRegistry\.register\(\s*['\"]([^'\"]+)['\"]"), ConfidenceLevel.MEDIUM),
    (re.compile(r"register_tool\(\s*['\"]([^'\"]+)['\"]"), ConfidenceLevel.MEDIUM),
    (re.compile(r"@tool\(\s*['\"]([^'\"]+)['\"]\s*\)"), ConfidenceLevel.MEDIUM),
]

TOOL_LIST_PATTERN = re.compile(r"(?:tools|agent_tools|function_tools)\s*=\s*\[([^\]]+)\]")
QUOTED_STRING_PATTERN = re.compile(r"['\"]([a-zA-Z][a-zA-Z0-9_.\-]{2,})['\"]")
DECORATOR_WITHOUT_NAME_PATTERN = re.compile(r"@tool\s*$")
FUNCTION_DEF_PATTERN = re.compile(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")
TOOL_MARKDOWN_TRIM_CHARS = "*_` "
HTTP_METHOD_ENDPOINT_PATTERN = re.compile(
    r"^(get|post|put|patch|delete|head|options)\s+/",
    flags=re.IGNORECASE,
)


DATA_SOURCE_HEURISTICS: dict[str, dict[str, Any]] = {
    "FHIR API": {
        "patterns": [r"\bfhir\b", r"\bhl7\b"],
        "type": "api",
        "interface": "FHIR/HL7",
    },
    "PostgreSQL": {
        "patterns": [r"postgres(?:ql)?://", r"psycopg", r"sqlalchemy\+postgresql"],
        "type": "database",
        "interface": "SQL",
    },
    "MySQL": {
        "patterns": [r"mysql://", r"pymysql", r"mysqlclient"],
        "type": "database",
        "interface": "SQL",
    },
    "Snowflake": {
        "patterns": [r"\bsnowflake\b", r"\bsnowflake[_-][a-zA-Z0-9_]+\b"],
        "type": "data_warehouse",
        "interface": "Snowflake",
    },
    "BigQuery": {
        "patterns": [r"\bbigquery\b", r"google\.cloud\.bigquery"],
        "type": "data_warehouse",
        "interface": "BigQuery",
    },
    "Amazon S3": {
        "patterns": [r"s3://", r"\bboto3\b", r"amazon s3"],
        "type": "object_storage",
        "interface": "S3",
    },
    "Google Cloud Storage": {
        "patterns": [r"gs://", r"google\.cloud\.storage", r"\bgcs\b"],
        "type": "object_storage",
        "interface": "GCS",
    },
    "Azure Blob Storage": {
        "patterns": [r"azure.*blob", r"abfs://"],
        "type": "object_storage",
        "interface": "Azure",
    },
    "Internal REST API": {
        "patterns": [r"https?://[a-zA-Z0-9_.\-]+(?:/[a-zA-Z0-9_./\-]*)?"],
        "type": "api",
        "interface": "REST",
    },
}


def normalize_tool_name(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def clean_tool_identifier(value: str) -> str:
    cleaned = value.strip().strip(TOOL_MARKDOWN_TRIM_CHARS)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def is_endpoint_like_tool(value: str) -> bool:
    normalized = clean_tool_identifier(value)
    return bool(HTTP_METHOD_ENDPOINT_PATTERN.match(normalized))


def load_allowed_tools(path: Path) -> list[AllowedTool]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as handle:
        parsed = yaml.safe_load(handle) or {}

    raw_tools = parsed.get("tools", []) if isinstance(parsed, dict) else []
    tools: list[AllowedTool] = []
    for entry in raw_tools:
        if not isinstance(entry, dict):
            continue
        tool_id = entry.get("tool_id")
        if not tool_id:
            continue
        tools.append(
            AllowedTool(
                tool_id=str(tool_id),
                tool_name=entry.get("tool_name"),
                expected_data_sources=[str(v) for v in entry.get("expected_data_sources", [])],
            )
        )
    return tools


def _is_text_candidate(path: Path) -> bool:
    if path.suffix.lower() in CODE_FILE_EXTENSIONS:
        return True
    return path.name in {".env", ".env.example"}


def _iter_source_files(repo_path: Path) -> list[Path]:
    files: list[Path] = []
    for path in repo_path.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SCAN_IGNORE_DIRS for part in path.parts):
            continue
        if _is_text_candidate(path):
            files.append(path)
    return files


def _confidence_for_path(path: Path) -> ConfidenceLevel:
    return ConfidenceLevel.MEDIUM if path.suffix.lower() in CONFIG_LIKE_EXTENSIONS else ConfidenceLevel.LOW


def _build_allowed_index(allowed_tools: list[AllowedTool]) -> dict[str, AllowedTool]:
    index: dict[str, AllowedTool] = {}
    for tool in allowed_tools:
        index[normalize_tool_name(tool.tool_id)] = tool
        if tool.tool_name:
            index[normalize_tool_name(tool.tool_name)] = tool
    return index


def _upsert_data_source(
    existing: dict[str, DataSourceRecord],
    name: str,
    source_type: str,
    interface_type: str,
    confidence: ConfidenceLevel,
    evidence: str,
) -> None:
    key = normalize_tool_name(name)
    current = existing.get(key)
    if current is None:
        existing[key] = DataSourceRecord(
            name=name,
            type=source_type,
            interface_type=interface_type,
            confidence=confidence,
            evidence=[evidence],
        )
        return

    if confidence == ConfidenceLevel.HIGH:
        current.confidence = confidence
    elif confidence == ConfidenceLevel.MEDIUM and current.confidence == ConfidenceLevel.LOW:
        current.confidence = confidence

    if evidence not in current.evidence:
        current.evidence.append(evidence)


def _infer_from_manifest(repo_path: Path) -> tuple[list[ToolRecord], dict[str, DataSourceRecord]]:
    manifest_paths = [repo_path / "agent.yaml", repo_path / "agent.yml"]
    manifest_path = next((path for path in manifest_paths if path.exists()), None)
    if manifest_path is None:
        return [], {}

    with manifest_path.open("r", encoding="utf-8") as handle:
        parsed = yaml.safe_load(handle) or {}

    tools: list[ToolRecord] = []
    data_sources: dict[str, DataSourceRecord] = {}

    for source in parsed.get("data_sources", []) if isinstance(parsed, dict) else []:
        if not isinstance(source, dict):
            continue
        name = str(source.get("name", "")).strip()
        if not name:
            continue
        _upsert_data_source(
            existing=data_sources,
            name=name,
            source_type=str(source.get("type", "unknown")),
            interface_type=str(source.get("environment", "unknown")),
            confidence=ConfidenceLevel.HIGH,
            evidence=f"{manifest_path}:data_sources",
        )

    for entry in parsed.get("tools", []) if isinstance(parsed, dict) else []:
        if not isinstance(entry, dict):
            continue
        tool_id_raw = str(entry.get("tool_id", "")).strip()
        tool_name_raw = str(entry.get("tool_name", tool_id_raw)).strip()
        tool_id = clean_tool_identifier(tool_id_raw)
        tool_name = clean_tool_identifier(tool_name_raw)

        primary_identifier = tool_id or tool_name
        if not primary_identifier:
            continue
        if is_endpoint_like_tool(primary_identifier):
            continue

        record = ToolRecord(
            tool_id=tool_id or tool_name,
            tool_name=tool_name or tool_id,
            purpose=entry.get("purpose"),
            permissions=[str(value) for value in entry.get("permissions", [])],
            confidence=ConfidenceLevel.HIGH,
            evidence=[f"{manifest_path}:tools"],
        )

        data_source_entries = entry.get("data_sources", [])
        for source in data_source_entries:
            if isinstance(source, str):
                name = source
                source_type = "unknown"
                environment = "unknown"
            elif isinstance(source, dict):
                name = str(source.get("name", "")).strip()
                source_type = str(source.get("type", "unknown"))
                environment = str(source.get("environment", "unknown"))
            else:
                continue

            if not name:
                continue

            ds = DataSourceRecord(
                name=name,
                type=source_type,
                environment=environment,
                confidence=ConfidenceLevel.HIGH,
                evidence=[f"{manifest_path}:tools:{tool_id or tool_name}"],
            )
            record.data_sources.append(ds)
            _upsert_data_source(
                existing=data_sources,
                name=name,
                source_type=source_type,
                interface_type="manifest",
                confidence=ConfidenceLevel.HIGH,
                evidence=f"{manifest_path}:tools",
            )

        tools.append(record)

    return tools, data_sources


def _infer_from_source(repo_path: Path) -> tuple[dict[str, ToolRecord], dict[str, list[DataSourceRecord]], dict[str, DataSourceRecord]]:
    tool_candidates: dict[str, ToolRecord] = {}
    data_sources_by_file: dict[str, list[DataSourceRecord]] = {}
    all_data_sources: dict[str, DataSourceRecord] = {}

    for file_path in _iter_source_files(repo_path):
        rel_path = str(file_path.relative_to(repo_path))
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()

        local_data_sources: dict[str, DataSourceRecord] = {}

        for index, line in enumerate(lines, start=1):
            for ds_name, ds_meta in DATA_SOURCE_HEURISTICS.items():
                for raw_pattern in ds_meta["patterns"]:
                    if re.search(raw_pattern, line, flags=re.IGNORECASE):
                        confidence = _confidence_for_path(file_path)
                        evidence = f"{rel_path}:{index}"
                        _upsert_data_source(
                            existing=local_data_sources,
                            name=ds_name,
                            source_type=ds_meta["type"],
                            interface_type=ds_meta["interface"],
                            confidence=confidence,
                            evidence=evidence,
                        )
                        _upsert_data_source(
                            existing=all_data_sources,
                            name=ds_name,
                            source_type=ds_meta["type"],
                            interface_type=ds_meta["interface"],
                            confidence=confidence,
                            evidence=evidence,
                        )

            if DECORATOR_WITHOUT_NAME_PATTERN.search(line):
                for lookahead in range(index, min(index + 4, len(lines))):
                    function_line = lines[lookahead]
                    match = FUNCTION_DEF_PATTERN.search(function_line)
                    if not match:
                        continue
                    tool_name = match.group(1)
                    key = normalize_tool_name(tool_name)
                    candidate = tool_candidates.get(key)
                    evidence = f"{rel_path}:{lookahead + 1}"
                    if candidate is None:
                        tool_candidates[key] = ToolRecord(
                            tool_id=tool_name,
                            tool_name=tool_name,
                            confidence=ConfidenceLevel.MEDIUM,
                            evidence=[evidence],
                        )
                    elif evidence not in candidate.evidence:
                        candidate.evidence.append(evidence)
                    break

            for pattern, confidence in TOOL_REGEX_PATTERNS:
                for match in pattern.finditer(line):
                    tool_name = match.group(1)
                    key = normalize_tool_name(tool_name)
                    evidence = f"{rel_path}:{index}"
                    candidate = tool_candidates.get(key)
                    if candidate is None:
                        tool_candidates[key] = ToolRecord(
                            tool_id=tool_name,
                            tool_name=tool_name,
                            confidence=confidence,
                            evidence=[evidence],
                        )
                    else:
                        if evidence not in candidate.evidence:
                            candidate.evidence.append(evidence)
                        if candidate.confidence == ConfidenceLevel.LOW and confidence != ConfidenceLevel.LOW:
                            candidate.confidence = confidence

            list_match = TOOL_LIST_PATTERN.search(line)
            if list_match:
                list_blob = list_match.group(1)
                for token in QUOTED_STRING_PATTERN.findall(list_blob):
                    key = normalize_tool_name(token)
                    evidence = f"{rel_path}:{index}"
                    candidate = tool_candidates.get(key)
                    if candidate is None:
                        tool_candidates[key] = ToolRecord(
                            tool_id=token,
                            tool_name=token,
                            confidence=ConfidenceLevel.LOW,
                            evidence=[evidence],
                        )
                    elif evidence not in candidate.evidence:
                        candidate.evidence.append(evidence)

        data_sources_by_file[rel_path] = list(local_data_sources.values())

    return tool_candidates, data_sources_by_file, all_data_sources


def infer_tools_and_data_sources(
    repo_path: Path,
    readme_tools: list[str],
    allowed_tools: list[AllowedTool],
) -> tuple[ToolBuckets, list[DataSourceRecord]]:
    allowed_index = _build_allowed_index(allowed_tools)

    manifest_tools, manifest_data_sources = _infer_from_manifest(repo_path)
    source_tools, data_sources_by_file, inferred_data_sources = _infer_from_source(repo_path)

    merged_tools: dict[str, ToolRecord] = {}
    for tool in manifest_tools:
        merged_tools[normalize_tool_name(tool.tool_id)] = tool

    for key, tool in source_tools.items():
        existing = merged_tools.get(key)
        if existing is None:
            inferred_ds_for_tool: list[DataSourceRecord] = []
            for evidence in tool.evidence:
                rel_path = evidence.split(":", 1)[0]
                inferred_ds_for_tool.extend(data_sources_by_file.get(rel_path, []))
            dedup: dict[str, DataSourceRecord] = {}
            for ds in inferred_ds_for_tool:
                dedup_key = normalize_tool_name(ds.name)
                if dedup_key not in dedup:
                    dedup[dedup_key] = ds
            tool.data_sources = list(dedup.values())
            merged_tools[key] = tool
            continue

        for evidence in tool.evidence:
            if evidence not in existing.evidence:
                existing.evidence.append(evidence)
        if existing.confidence == ConfidenceLevel.LOW and tool.confidence != ConfidenceLevel.LOW:
            existing.confidence = tool.confidence
        if not existing.data_sources:
            existing.data_sources = tool.data_sources

    buckets = ToolBuckets()

    for key, tool in sorted(merged_tools.items(), key=lambda item: item[0]):
        matched_allowlist = allowed_index.get(key)
        if matched_allowlist is not None:
            tool.status = ToolVerificationStatus.VERIFIED
            tool.tool_id = matched_allowlist.tool_id
            if matched_allowlist.tool_name:
                tool.tool_name = matched_allowlist.tool_name
            if not tool.data_sources and matched_allowlist.expected_data_sources:
                tool.data_sources = [
                    DataSourceRecord(
                        name=name,
                        type="unknown",
                        confidence=ConfidenceLevel.MEDIUM,
                        evidence=["allowed_tools"],
                    )
                    for name in matched_allowlist.expected_data_sources
                ]
            buckets.verified.append(tool)
        else:
            tool.status = ToolVerificationStatus.UNVERIFIED
            buckets.unverified.append(tool)

    inferred_keys = {
        normalize_tool_name(tool.tool_id)
        for tool in buckets.verified + buckets.unverified
    }

    for documented in sorted(set(readme_tools), key=str.lower):
        cleaned_documented = clean_tool_identifier(documented)
        if not cleaned_documented or is_endpoint_like_tool(cleaned_documented):
            continue

        key = normalize_tool_name(cleaned_documented)
        if key in inferred_keys:
            continue

        buckets.doc_only.append(
            ToolRecord(
                tool_id=cleaned_documented,
                tool_name=cleaned_documented,
                status=ToolVerificationStatus.DOC_ONLY,
                confidence=ConfidenceLevel.LOW,
                evidence=["README"],
            )
        )

    all_data_sources: dict[str, DataSourceRecord] = {}
    for ds in list(manifest_data_sources.values()) + list(inferred_data_sources.values()):
        merge_key = normalize_tool_name(ds.name)
        current = all_data_sources.get(merge_key)
        if current is None:
            all_data_sources[merge_key] = ds
            continue

        if ds.confidence == ConfidenceLevel.HIGH:
            current.confidence = ConfidenceLevel.HIGH
        elif ds.confidence == ConfidenceLevel.MEDIUM and current.confidence == ConfidenceLevel.LOW:
            current.confidence = ConfidenceLevel.MEDIUM

        for evidence in ds.evidence:
            if evidence not in current.evidence:
                current.evidence.append(evidence)

    return buckets, sorted(all_data_sources.values(), key=lambda item: item.name.lower())







