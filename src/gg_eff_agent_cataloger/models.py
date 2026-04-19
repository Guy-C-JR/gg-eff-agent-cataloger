from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ReadmeStatus(str, Enum):
    MISSING = "missing"
    OK = "ok"
    NEEDS_UPDATE = "needs_update"


class ToolVerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    DOC_ONLY = "DOC_ONLY"


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DataSourceRecord(BaseModel):
    name: str
    type: str
    interface_type: str | None = None
    environment: str | None = None
    owner: str | None = None
    notes: str | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    evidence: list[str] = Field(default_factory=list)


class ToolRecord(BaseModel):
    tool_id: str
    tool_name: str
    purpose: str | None = None
    inputs: str | None = None
    outputs: str | None = None
    permissions: list[str] = Field(default_factory=list)
    data_sources: list[DataSourceRecord] = Field(default_factory=list)
    status: ToolVerificationStatus = ToolVerificationStatus.UNVERIFIED
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    evidence: list[str] = Field(default_factory=list)


class ToolBuckets(BaseModel):
    verified: list[ToolRecord] = Field(default_factory=list)
    unverified: list[ToolRecord] = Field(default_factory=list)
    doc_only: list[ToolRecord] = Field(default_factory=list)


class RepoIssue(BaseModel):
    code: str
    severity: str
    message: str
    suggestion: str | None = None
    path: str | None = None


class RepoReport(BaseModel):
    agent_name: str
    repo: str
    default_branch: str | None = None
    repo_reachable: bool = False
    clone_succeeded: bool = False
    synced_with_remote: bool = False
    local_head: str | None = None
    remote_head: str | None = None
    last_commit_date: str | None = None
    latest_release_tag: str | None = None
    latest_release_date: str | None = None
    ci_workflows: list[str] = Field(default_factory=list)
    readme_status: ReadmeStatus = ReadmeStatus.MISSING
    readme_path: str | None = None
    required_sections_present: list[str] = Field(default_factory=list)
    required_sections_missing: list[str] = Field(default_factory=list)
    tools: ToolBuckets = Field(default_factory=ToolBuckets)
    data_sources: list[DataSourceRecord] = Field(default_factory=list)
    issues: list[RepoIssue] = Field(default_factory=list)
    score: int = 0
    apply_changes: list[str] = Field(default_factory=list)
    pr_url: str | None = None


class CatalogReport(BaseModel):
    generated_at: datetime
    org: str
    repos_scanned: int
    agents: list[RepoReport] = Field(default_factory=list)


class ReadmeAnalysisResult(BaseModel):
    status: ReadmeStatus
    path: str | None = None
    present_sections: list[str] = Field(default_factory=list)
    missing_sections: list[str] = Field(default_factory=list)
    content: str = ""


class AllowedTool(BaseModel):
    tool_id: str
    tool_name: str | None = None
    expected_data_sources: list[str] = Field(default_factory=list)


class AppConfig(BaseModel):
    org: str
    repos: list[str] = Field(default_factory=list)
    agents: dict[str, str] = Field(default_factory=dict)
    discover: bool = False
    keywords: list[str] = Field(default_factory=list)
    out: str = "catalog"
    clone_dir: str | None = None
    local_repos_dir: str | None = None
    allowed_tools_file: str = "config/allowed_tools.yaml"
    apply: bool = False
    pr: bool = False
    privacy_safe_logging: bool = True
    token_env: str = "GITHUB_TOKEN"
    github_base_url: str | None = None


class RunSummary(BaseModel):
    repos_scanned: int
    repos_passed_required_checks: int
    repos_failed_required_checks: int
    missing_readme_count: int
    missing_tools_data_sources_section_count: int
    unverified_tool_count: int


def jsonable_model(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")
