---
name: review-api-change
description: Check an EFINGES API change across backend, contract, frontend, and access rules.
agent: agent
---

Review the current changes that affect the EFINGES API. Trace each changed
endpoint through its router, schemas, access helpers, tests, generated
`openapi.yaml`, and every affected frontend call. Check role and property
scoping, validation, status codes, migration implications, and whether the
contract is current. Report only concrete, actionable issues with file and
line references; do not modify files unless asked.
