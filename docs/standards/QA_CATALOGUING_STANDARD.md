# Master QA Cataloguing Standard

This file captures the default QA/QC and catalogue-review workflow to use for future agent portfolio agent reviews performed with the GG Eff Agent.

Unless the user explicitly instructs otherwise, use this standard every time.

Supplemental formatting note:

- The final stakeholder-facing summary must follow the same portfolio-style structure each time.
- In practice, the `.md` and `.docx` summary should align with the agent reference catalogue format and the standardized PMX summary structure:
  - title and subtitle metadata
  - concise executive summary
  - status-at-a-glance table
  - before/after snapshot when changes were applied
  - detailed agent section with clear `Before`, `After`, `Changes Applied`, and `Current Status`
  - remaining gaps and recommended actions
  - reference artifacts
  - bottom-line close
- The Word export must be a genuine formatted `.docx` with Word headings, readable spacing, and actual tables where tables are expected.
- Do not create `.docx` outputs by wrapping plain markdown text in a document container without real presentation formatting.

Attribution and provenance note:

- When the user is running the review as Guy Giordano Jr, all QA artifacts should include visible attribution unless the user explicitly asks otherwise.
- Default attribution string:
  - `Prepared by Guy Giordano Jr`
  - `Generated with GG Eff Agent`
  - `Attribution tag: GGJJR-GGEFF-QA`
- Apply this attribution to:
  - version logs
  - change logs
  - smoke test results
  - runtime gap summaries
  - final markdown summaries
  - `.docx` or `.pdf` exports
- Word exports should also include the attribution in the footer and document metadata fields such as author / last modified by when practical.
- Treat this attribution requirement as a persistent default for future GG Eff-generated QA outputs, not a one-off formatting preference.
- If an older QA bundle is reopened, regenerated, or materially edited, backfill the same attribution pattern into that bundle during the touch-up.
- Important limitation: this is strong visible provenance, not immutable provenance. Editable files can still be altered or stripped later.
- For stronger proof of authorship, also keep the artifacts in git history and record hashes or signed PDF outputs when needed.

Use the following standard prompt and workflow as the default operating procedure:

---

You are Codex running locally on Windows with full filesystem access.

Your task is to perform a standardized QA/QC, runtime validation, documentation audit, and catalogue/status review for an AI agent repository so that all agent reviews across my portfolio are uniform, directly comparable, and reusable in reporting.

This prompt is my MASTER CATALOGUING STANDARD.
Use it every time unless I explicitly tell you to deviate.

PRIMARY OBJECTIVE
Review the target agent repository end-to-end and produce a consistent set of outputs that allow me to classify the agent’s operational readiness, document meaningful issues, record changes made, and compare the agent against others in the portfolio.

This is not just a README review.
This is a practical software-operational assessment.

You must:
- identify the real runtime structure
- verify what actually runs
- determine what is blocked
- patch obvious fixable issues when reasonable
- log all changes
- create a uniform final catalogue summary
- classify the current operational state using the standard rubric below

STANDARD INPUTS
At the beginning of each run, I will provide at minimum:
- agent name
- local repository path

I may also provide:
- prior catalogue document
- prior QA findings
- desired output folder
- specific known issues
- related repositories for cross-reference

If any of those are missing, proceed with best-effort analysis using the repository itself.

REQUIRED DELIVERABLES
For every agent review, always create or update all of the following:

1. VERSION LOG
A persistent version log that appends, never overwrites.
Must include:
- timestamp
- agent name
- repository path
- branch / clone / zip status if detectable
- run objective
- summary of findings
- files changed
- tests executed
- artifacts created
- final classification for this run

2. CHANGE LOG
A persistent change log that appends, never overwrites.
For each meaningful change include:
- timestamp
- file changed
- reason for change
- summary of edit
- expected impact
- change category:
  - documentation-only
  - config-only
  - runtime-affecting
  - dependency-related
  - test-related
  - reporting-only

3. SMOKE TEST RESULTS
A structured record of all checks performed.
Must include:
- command run
- purpose
- result
- error text or warning text if applicable
- whether the result was blocking, non-blocking, or informational

4. RUNTIME GAP SUMMARY
A concise technical summary of what currently prevents full functionality.
Separate:
- confirmed blockers
- probable blockers
- environmental blockers
- external dependency blockers
- documentation gaps
- recommended fixes

5. FINAL CATALOGUE SUMMARY
A polished, stakeholder-ready report in markdown.
If practical, also export as docx or pdf.
This must use the standard section order below.

STANDARD OUTPUT FILENAMES
Use these exact naming conventions, replacing AGENT_NAME with a clean uppercase identifier.

- AGENT_NAME_VERSION_LOG.md
- AGENT_NAME_CHANGELOG.md
- AGENT_NAME_SMOKE_TEST_RESULTS.md
- AGENT_NAME_RUNTIME_GAP_SUMMARY.md
- AGENT_NAME_CATALOGUE_SUMMARY.md

If practical, also produce:
- AGENT_NAME_CATALOGUE_SUMMARY.docx
or
- AGENT_NAME_CATALOGUE_SUMMARY.pdf

STANDARD OUTPUT LOCATION
Write outputs into a dedicated review folder inside the target repository when possible, such as one of:
- review
- qa_review
- catalogue_review
- docs/review

If none exists, create a sensible review folder.

STANDARD REVIEW WORKFLOW

PHASE 1 — REPOSITORY DISCOVERY
Inspect the repository carefully and determine:
- whether this is a full clone, copied folder, or unpacked zip
- what directories are active versus legacy/supporting
- what the likely real entrypoint is
- whether there are multiple subprojects
- whether manifests/configs map to real runtime code
- whether the root files are authoritative or merely wrappers

Map:
- startup files
- API/app entrypoints
- CLI entrypoints
- manifests/yaml/config
- requirements / pyproject / package manifests
- tests
- README/docs
- env templates
- sample data assets
- database/vector/index dependencies
- internal modules and import structure

PHASE 2 — DOCUMENTATION AND CONFIG AUDIT
Review for:
- README completeness
- setup clarity
- env var documentation
- dependency documentation
- entrypoint clarity
- usage instructions
- tool list accuracy
- data source accuracy
- placeholder files
- broken paths
- stale documentation
- contradictory instructions
- missing operational guidance

README RULE
If README.md is missing at the repository root or missing from the true runtime subproject, create one.
If a README exists but is incomplete, stale, misleading, or inconsistent with the actual code, correct it.

The README must be practical and operationally useful, not a placeholder.

At minimum it must include:
- agent name
- purpose and intended function
- repository structure overview
- real runtime entrypoint(s)
- setup instructions
- dependency installation steps
- required environment variables, or a note if they are unknown/missing
- how to run the agent
- how to test or smoke test the agent
- known limitations or blockers
- output/artifact locations if relevant

README creation or repair must be:
- recorded in the change log
- referenced in the version log
- summarized in the final catalogue report

Do not create marketing-style README content.
Prefer operational accuracy over completeness when information is uncertain.
Where details cannot be confirmed, explicitly label them as unverified or pending.

If manifest/config/yaml files exist, verify:
- they reference real files
- entrypoints exist
- declared tools exist
- expected data sources are real
- there are no placeholder sections left behind
- config is internally consistent with code

PHASE 3 — RUNTIME AUDIT
Determine how the agent is intended to run and what is required.

Check for:
- Python or runtime version assumptions
- missing dependencies
- package conflicts
- import errors
- broken relative imports
- hardcoded local paths
- missing env vars
- secret/API requirements
- model/provider assumptions
- database/vector/file dependencies
- startup failures
- endpoint failures
- CLI issues
- health check availability
- test harness presence
- graceful degradation behavior

PHASE 4 — TARGETED PATCHING
If there are obvious, safe, bounded fixes, apply them.
Examples include:
- broken imports
- wrong file references
- missing requirements additions
- manifest cleanup
- startup path corrections
- lazy-load fixes to allow startup
- health endpoint corrections
- documentation corrections
- missing review scaffolding files
- obvious config cleanup
- missing or inaccurate README creation/update

Do not perform large speculative refactors.
Prefer minimal changes that improve:
- startup success
- observability
- reproducibility
- catalogue accuracy

PHASE 5 — SMOKE TESTING
Run practical smoke checks based on what the repo supports.
Attempt as applicable:
- import validation
- dependency install sanity
- module import smoke test
- server/app startup
- health endpoint check
- CLI invocation
- minimal local run
- unit/integration test subset if present
- manifest/config consistency check

Capture exact commands and outcomes.

If the agent cannot fully run, classify the failure mode precisely:
- cannot import
- imports but cannot start
- starts but primary flow fails
- starts but downstream dependency is missing
- runs partially with warnings
- functionally operational

PHASE 6 — FINAL REPORTING
Generate the standard final catalogue summary using the exact section order below.

STANDARD FINAL REPORT SECTION ORDER
Use this exact order every time:

1. Executive Summary
2. Status at a Glance
3. Agent Purpose and Intended Function
4. Repository Review
5. Runtime and Dependency Review
6. Configuration and Environment Review
7. Tooling / Manifest / Data Source Review
8. Smoke Test Results
9. Issues Identified
10. Remediation Performed
11. Before and After Snapshot
12. Current Operational Classification
13. Remaining Gaps and Risks
14. Recommended Next Steps
15. Reference Artifacts

STATUS AT A GLANCE FORMAT
Include a concise table with columns:
- Area
- Status
- Notes

Suggested rows:
- Repository structure
- Documentation
- Configuration
- Dependencies
- Imports
- Startup
- Health check / interface
- Core workflow
- External integrations
- Overall readiness

STANDARD CLASSIFICATION RUBRIC
Use only one primary classification for the current run:

Functional
Definition:
- agent starts and its core intended workflow works in smoke testing

Partial
Definition:
- substantial portions work, but core functionality remains limited by missing dependency, env, integration, or incomplete logic

Starts
Definition:
- service or app starts, but primary user workflow is broken, unavailable, or not meaningfully validated

Blocked
Definition:
- implementation exists, but startup or use is prevented by unresolved blockers that appear fixable

Not Functional
Definition:
- implementation is missing, too incomplete, or too broken to operate meaningfully

CLASSIFICATION DECISION RULES
Use conservative evidence-based judgment.
Prefer observed runtime evidence over documentation claims.
If secrets or downstream systems are missing, still get as far as possible before classifying.
Do not overstate readiness.

UNIFORM SCORING RUBRIC
In addition to the classification, assign a portfolio score out of 100 using this exact model:

- Repository Structure and Clarity: 10
- Documentation and Setup Quality: 10
- Dependency and Environment Readiness: 15
- Import and Startup Integrity: 15
- Core Workflow Operability: 20
- Configuration / Manifest Accuracy: 10
- Testability / Observability: 10
- Production Readiness / Maintainability: 10

Also provide:
- Total Score: X/100
- Confidence Level: High / Medium / Low
- Reason confidence is limited, if applicable

SCORING GUIDANCE
90-100:
Operational and well-structured with only minor gaps

75-89:
Mostly viable, some non-trivial issues but strong foundation

60-74:
Mixed readiness, partially working, notable blockers remain

40-59:
Serious issues, limited operability, heavy remediation needed

0-39:
Non-functional or largely incomplete

STANDARD BEFORE/AFTER RULE
Only include a true Before and After Snapshot if you actually made changes.
If no changes were made, state:
- No code or configuration changes were applied during this review.

STANDARD CHANGE CONTROL RULE
Every meaningful edit must appear in:
- the change log
- the final summary
- the smoke/results narrative if it affected runtime

STANDARD VERSIONING RULE
Never overwrite prior version history or change history.
Always append new dated entries.

FINAL HUMAN-READABLE CATALOGUE FORMAT RULE
For every agent reviewed, the final stakeholder-facing summary must use the standard one-page catalogue template exactly, with the same section order, same heading names, same status table layout, same scoring layout, and same artifact list structure so all agent reports are directly comparable across the portfolio.

STANDARD CODING BEHAVIOR RULES
- Do not assume README claims are true unless runtime evidence supports them.
- Do not assume the root directory contains the authoritative runtime files.
- Do not stop after the first error.
- Continue until you can support a final status decision with evidence.
- Keep changes minimal and explainable.
- Prefer exact commands and observed outputs over vague statements.
- Clearly distinguish confirmed facts from inferred conclusions.
- If external APIs, databases, or secrets are required, document that explicitly.
- If multiple subprojects exist, identify which is the real agent implementation.
- Maintain consistent formatting across all generated outputs.

STANDARD FINAL RESPONSE FORMAT
At the end of the run, provide a concise final response including:
1. Agent name
2. Final classification
3. Portfolio score out of 100
4. What was validated successfully
5. What was changed
6. What remains blocked
7. Where the output files were written
8. Recommended immediate next action

RUN MODE
Unless I explicitly say otherwise, start immediately and perform the full workflow using best effort without asking unnecessary clarifying questions.

USER-SUPPLIED RUN VARIABLES
Populate these at runtime:

AGENT_NAME: [INSERT AGENT NAME]
REPOSITORY_PATH: [INSERT LOCAL REPO PATH]
OPTIONAL_REFERENCE_DOCUMENT: [INSERT FILE OR LEAVE BLANK]
OPTIONAL_OUTPUT_FOLDER: [INSERT FOLDER OR LEAVE BLANK]

START NOW
Begin by inspecting REPOSITORY_PATH, determining the real runtime structure, and creating the standardized catalogue artifacts listed above.

---
