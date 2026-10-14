---
name: diagnose-failing-check
description: Diagnose a failing EFINGES check from evidence before proposing a fix.
agent: agent
---

Diagnose this failing check: **${input:check_or_error}**.

Read the relevant project instructions and test output, reproduce the failure
with the narrowest command, and trace it to its cause before editing. Avoid
loosening assertions or suppressing errors. Make the smallest root-cause fix,
add or update a regression test, run the focused check and any directly
affected checks, and summarize evidence and results. Do not commit unless
explicitly requested.
