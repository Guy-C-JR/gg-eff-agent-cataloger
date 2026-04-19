# GG Eff Agent Cataloger

Recruiter-facing project page: https://guy-c-jr.github.io/gg-eff-agent-cataloger/

GG Eff Agent Cataloger is a Python CLI for auditing agent repositories, validating documentation completeness, inferring tool/data-source usage, checking runtime gaps, and generating reusable portfolio catalogue artifacts.

## Why This Project Matters

This repository packages the `gg_eff_agent_cataloger` tool from the GG Eff Agents archive into a public, portfolio-safe form. It highlights agent QA and documentation automation:

- GitHub or local-repository scanning for agent projects
- README completeness checks against required operational sections
- Broken local-link detection
- Tool and data-source inference from manifests, source code, configs, and README content
- Allowlist validation for documented or inferred tools
- Dry-run default behavior, with apply mode for README/manifest scaffolding
- Markdown and JSON report generation for cross-agent portfolio review

## Repository Map

- `src/gg_eff_agent_cataloger`: CLI, runner, config, GitHub client, git operations, README analysis, tool inference, scoring, apply mode, and report writers.
- `tests`: pytest coverage for config, GitHub client behavior, local mode, runner integration, reporting, README analysis, and tool inference.
- `config`: public templates, schema, and allowed-tool definitions.
- `docs/standards`: QA catalogue standard and repository instructions.
- `site`: static GitHub Pages case study.

## Technical Highlights

### Agent Repository QA

- Scans local or remote agent repositories
- Identifies README gaps, stale operational docs, and broken local links
- Resolves common ZIP/folder suffixes for local review mode
- Infers repo health and branch currency where git metadata is available

### Tool and Data-Source Inference

- Reads `agent.yaml`, source files, config files, and README sections
- Compares documented tools against observed implementation signals
- Flags unverified tools and documentation-only claims
- Tracks data-source signals such as FHIR/HL7 APIs, SQL stores, object stores, and internal REST APIs

### Portfolio-Ready Reporting

- Produces `GG_EFF_AGENT_CATALOG.md`, per-repo markdown reports, machine-readable JSON, and TODO lists
- Scores repositories from 0 to 100 based on documentation, implementation, sync, and verification findings
- Keeps QA outputs comparable across agents through a standard catalogue structure

## Evidence Anchors

- CLI entrypoint: `src/gg_eff_agent_cataloger/cli.py`
- Runner orchestration: `src/gg_eff_agent_cataloger/runner.py`
- README audit engine: `src/gg_eff_agent_cataloger/readme_analysis.py`
- Tool inference: `src/gg_eff_agent_cataloger/tool_inference.py`
- Scoring: `src/gg_eff_agent_cataloger/scoring.py`
- Apply mode: `src/gg_eff_agent_cataloger/apply_mode.py`
- Report writing: `src/gg_eff_agent_cataloger/reporting.py`
- QA standard: `docs/standards/QA_CATALOGUING_STANDARD.md`

## Local Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest -q
```

Run a local catalogue scan:

```bash
gg_eff_agent_cataloger \
  --local-repos-dir ./agents \
  --discover \
  --keywords ehr,pgx,rx,agent \
  --allowed-tools config/allowed_tools.yaml \
  --out catalog
```

Remote mode reads the token from `GITHUB_TOKEN`. Keep tokens in the environment only; do not commit credentials.

## Portfolio Positioning

The strongest claim for this project is portfolio operations engineering: it standardizes how agent repositories are reviewed, scored, repaired, and summarized. It is useful because it turns messy agent folders into comparable artifacts for QA, documentation, and recruiter-facing evidence.

This public version intentionally excludes local databases, virtual environments, generated JSON catalogs, private runtime artifacts, and local review-output bundles.
