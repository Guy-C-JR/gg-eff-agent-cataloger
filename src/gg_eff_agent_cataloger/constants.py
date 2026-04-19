from __future__ import annotations

from typing import Final

DEFAULT_AGENT_KEYWORDS: Final[list[str]] = [
    "ehr",
    "phenotype",
    "pgx",
    "pmx",
    "gwas",
    "rx",
    "agent",
]

REQUIRED_README_SECTIONS: Final[dict[str, list[str]]] = {
    "Overview": ["overview", "about", "introduction", "summary"],
    "Quickstart": ["quickstart", "quick start", "getting started"],
    "Installation / Setup": ["installation", "setup", "install"],
    "Configuration": ["configuration", "config", "settings"],
    "Tools & Data Sources": [
        "tools and data sources",
        "tools & data sources",
        "tools and data",
        "tooling",
    ],
    "Examples": ["examples", "usage examples", "sample usage"],
    "Testing": ["testing", "tests", "quality checks"],
    "Safety / Compliance Notes": [
        "safety",
        "compliance",
        "security",
        "privacy handling",
    ],
    "Repository Structure": [
        "repository structure",
        "project structure",
        "code structure",
        "layout",
    ],
    "Changelog / Versioning": ["changelog", "versioning", "release notes", "versions"],
}

CODE_FILE_EXTENSIONS: Final[set[str]] = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".yaml",
    ".yml",
    ".toml",
    ".json",
    ".env",
    ".ini",
    ".cfg",
    ".md",
}

CONFIG_LIKE_EXTENSIONS: Final[set[str]] = {
    ".yaml",
    ".yml",
    ".toml",
    ".json",
    ".env",
    ".ini",
    ".cfg",
}

SCAN_IGNORE_DIRS: Final[set[str]] = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
}

README_CANDIDATES: Final[list[str]] = ["README.md", "readme.md", "README.mdx", "readme.mdx"]
