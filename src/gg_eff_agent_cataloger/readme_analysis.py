from __future__ import annotations

import re
from pathlib import Path

from .constants import README_CANDIDATES, REQUIRED_README_SECTIONS
from .models import ReadmeAnalysisResult, ReadmeStatus


LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
HTTP_ENDPOINT_CANDIDATE_PATTERN = re.compile(
    r"^(get|post|put|patch|delete|head|options)\s+/",
    flags=re.IGNORECASE,
)


def normalize_heading(heading: str) -> str:
    lowered = heading.strip().lower()
    return " ".join(part for part in re.split(r"[^a-z0-9]+", lowered) if part)


def _clean_tool_candidate(value: str) -> str:
    cleaned = value.strip()
    cleaned = cleaned.strip("*_` ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _is_endpoint_style_candidate(value: str) -> bool:
    return bool(HTTP_ENDPOINT_CANDIDATE_PATTERN.match(value.strip()))


def find_root_readme(repo_path: Path) -> Path | None:
    for candidate in README_CANDIDATES:
        path = repo_path / candidate
        if path.exists() and path.is_file():
            return path
    return None


def extract_markdown_headings(markdown_text: str) -> list[str]:
    headings: list[str] = []
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        heading = re.sub(r"^#+\s*", "", stripped).strip()
        if heading:
            headings.append(normalize_heading(heading))
    return headings


def evaluate_readme_text(markdown_text: str) -> tuple[list[str], list[str]]:
    normalized_headings = extract_markdown_headings(markdown_text)

    present: list[str] = []
    missing: list[str] = []

    for canonical, aliases in REQUIRED_README_SECTIONS.items():
        alias_norm = [normalize_heading(alias) for alias in aliases]
        matched = False
        for heading in normalized_headings:
            if any(alias in heading for alias in alias_norm):
                matched = True
                break
        if matched:
            present.append(canonical)
        else:
            missing.append(canonical)

    return present, missing


def analyze_readme(repo_path: Path) -> ReadmeAnalysisResult:
    readme_path = find_root_readme(repo_path)
    if readme_path is None:
        return ReadmeAnalysisResult(status=ReadmeStatus.MISSING)

    content = readme_path.read_text(encoding="utf-8", errors="ignore")
    present, missing = evaluate_readme_text(content)

    status = ReadmeStatus.OK if not missing else ReadmeStatus.NEEDS_UPDATE
    return ReadmeAnalysisResult(
        status=status,
        path=str(readme_path),
        present_sections=present,
        missing_sections=missing,
        content=content,
    )


def _extract_section_block(markdown_text: str, heading_aliases: list[str]) -> str:
    aliases = [normalize_heading(alias) for alias in heading_aliases]
    lines = markdown_text.splitlines()

    start_index: int | None = None
    end_index: int | None = None

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        heading = normalize_heading(re.sub(r"^#+\s*", "", stripped).strip())
        if start_index is None and any(alias in heading for alias in aliases):
            start_index = idx + 1
            continue
        if start_index is not None:
            end_index = idx
            break

    if start_index is None:
        return ""

    if end_index is None:
        end_index = len(lines)

    return "\n".join(lines[start_index:end_index])


def extract_documented_tools(markdown_text: str) -> list[str]:
    tools_block = _extract_section_block(
        markdown_text,
        [
            "tools & data sources",
            "tools and data sources",
            "tools",
            "tooling",
        ],
    )
    if not tools_block:
        return []

    candidates: set[str] = set()

    for line in tools_block.splitlines():
        bullet_match = re.match(r"^\s*[-*+]\s+(.+)$", line.strip())
        if bullet_match:
            raw = bullet_match.group(1)
            raw = raw.split(":", 1)[0]
            raw = raw.split(" - ", 1)[0]
            normalized = _clean_tool_candidate(raw.replace("`", ""))
            if normalized and len(normalized) > 2 and not _is_endpoint_style_candidate(normalized):
                candidates.add(normalized)

        for inline_code in re.findall(r"`([a-zA-Z][a-zA-Z0-9_.\-]+)`", line):
            if len(inline_code) > 2:
                candidates.add(inline_code)

    generic_words = {
        "tools",
        "data",
        "sources",
        "source",
        "api",
        "database",
        "storage",
        "permissions",
    }

    filtered = [
        candidate
        for candidate in candidates
        if candidate.lower() not in generic_words
        and not _is_endpoint_style_candidate(candidate)
    ]
    return sorted(set(filtered), key=str.lower)


def find_broken_local_links(repo_path: Path, markdown_text: str) -> list[str]:
    broken: list[str] = []
    for raw_link in LINK_PATTERN.findall(markdown_text):
        link = raw_link.strip()
        if not link:
            continue
        if link.startswith(("http://", "https://", "mailto:", "#")):
            continue

        cleaned = link.split("#", 1)[0].strip()
        if not cleaned:
            continue

        target = (repo_path / cleaned).resolve()
        if not target.exists():
            broken.append(link)

    return sorted(set(broken), key=str.lower)




