from gg_eff_agent_cataloger.readme_analysis import evaluate_readme_text, extract_documented_tools


def test_readme_fuzzy_headings_cover_required_sections() -> None:
    readme = """
# Agent

## Introduction

## Getting Started

## Setup

## Config

## Tools and Data Sources

## Usage Examples

## Tests

## Safety

## Project Structure

## Release Notes
"""
    present, missing = evaluate_readme_text(readme)

    assert "Overview" in present
    assert "Quickstart" in present
    assert "Installation / Setup" in present
    assert "Tools & Data Sources" in present
    assert missing == []


def test_extract_documented_tools_from_tools_section() -> None:
    readme = """
## Tools & Data Sources
- `fetch_fhir_patient`: Fetches patient data
- query_ehr_db - SQL query helper
"""

    tools = extract_documented_tools(readme)

    assert "fetch_fhir_patient" in tools
    assert "query_ehr_db" in tools


def test_extract_documented_tools_ignores_http_endpoint_bullets() -> None:
    readme = """
## Tools & Data Sources
- **POST /process**: Run process endpoint
- **POST /convert/csv**: Convert to CSV
- **query_ehr_db**: SQL query helper
"""

    tools = extract_documented_tools(readme)

    assert "query_ehr_db" in tools
    assert "POST /process" not in tools
    assert "POST /convert/csv" not in tools
