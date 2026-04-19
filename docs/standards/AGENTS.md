# Repository Instructions

## Change Logging

For any future edit to this repository, maintain a running record in `CHANGE_HISTORY.md`.

Each change entry must include:

- date
- actor
- files changed
- prior state
- change made
- reason for the change
- validation or follow-up notes

Use the existing format in `CHANGE_HISTORY.md` and append new entries in reverse chronological order.

## Scope

Apply this requirement to:

- code changes
- prompt or agent behavior changes
- README or documentation edits
- config changes
- test changes
- release-management changes

If multiple files are edited for one logical change, record them in a single entry unless separate entries would be clearer.

## Portfolio QA Standard

For any future QA/QC, runtime validation, documentation audit, or catalogue/status review performed with this repository, follow `QA_CATALOGUING_STANDARD.md` unless the user explicitly instructs otherwise.

That standard is the default operating procedure for portfolio reviews and should control:

- required deliverables
- append-only version and change logging
- smoke-test recording
- runtime-gap summaries
- scoring and classification
- README repair expectations
- final stakeholder-facing summary structure

The final `.md` and `.docx` catalogue summaries must use the same standardized portfolio-oriented structure each time so outputs remain directly comparable across agents.

When the operator is Guy Giordano Jr, all GG Eff-generated QA artifacts must include the standard attribution block and, for Word exports, footer/metadata attribution as defined in `QA_CATALOGUING_STANDARD.md`.
