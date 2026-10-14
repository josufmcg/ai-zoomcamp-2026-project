# Security and audit artifacts

This directory holds the deterministic security scans for EFINGES and the
triage of their results (backlog task 21). The reports are snapshots: they are
committed so a reviewer can see exactly what the scanners found at the time of
the scan, and every one of them can be reproduced with the commands below.

| File | What it is |
| --- | --- |
| `bandit-report.txt` | Static analysis of the backend Python code (Bandit). |
| `trivy-backend.txt` | Vulnerability scan of the backend Docker image (`Dockerfile.backend`). |
| `trivy-frontend.txt` | Vulnerability scan of the frontend Docker image (`Dockerfile.frontend`). |
| `trivy-report.tpl` | The Trivy template used to render the two image reports. |

## Reproducing the scans

Bandit runs ad hoc through `uvx`, so it is not a project dependency:

```bash
cd backend
uvx bandit -r app scripts alembic --exclude alembic/versions -f txt
```

Trivy is a separate binary. Install it (or use the official container image)
and render the reports with the committed template, which emits a stable,
tab-separated line per finding instead of Trivy's terminal-width-dependent
table:

```bash
make up                                  # build the efinges-backend/frontend images
trivy image --scanners vuln --format template \
    --template '@security/trivy-report.tpl' efinges-backend:local
trivy image --scanners vuln --format template \
    --template '@security/trivy-report.tpl' efinges-frontend:local
```

The `make security` target runs both scanners and rewrites all three reports.

## Bandit triage (backend Python)

Result: **0 High, 0 Medium, 27 Low**. All 27 findings are in the developer
tooling under `backend/scripts/`; the shipped application code under
`backend/app/` produces **no** findings. Because the findings are confined to
scripts that only run locally, none of them are reachable from the API.

| Test | Count | Files | Severity | Assessment |
| --- | --- | --- | --- | --- |
| B101 `assert_used` | 20 | `scripts/e2e_smoke.py`, `scripts/scope_audit.py` | Low | Expected. These scripts are throwaway verification harnesses; `assert` is the intended way to fail them. `python -O` is not used anywhere. |
| B105 / B106 hard-coded password | 4 | `scripts/e2e_smoke.py`, `scripts/scope_audit.py` | Low | Test-only credentials (`password123`, throwaway 32-byte `secret_key` values) for accounts that exist only in the disposable verification run. They are not real secrets and never reach a deployed environment. |
| B404 `import_subprocess` | 1 | `scripts/check_staged_secrets.py` | Low | Required: the pre-commit hook reads `git diff --cached`. |
| B603 / B607 subprocess call | 2 | `scripts/check_staged_secrets.py` | Low | `git` is invoked with a fixed argument list and `shell=False`; there is no untrusted input. B607 flags the bare `git` name. |

No action items: the scan of the code that actually ships is clean, and the
remaining findings are inherent to local developer scripts.

## Trivy triage (container images)

Both images are built from official base images (`python:3.12-slim` and
`nginx:1.27-alpine`). The great majority of the findings are operating-system
packages that ship inside those base images, not code from this repository.
The EFINGES application layers add no vulnerabilities of their own.

### Backend image — 172 findings (0 Critical, 44 High, 63 Medium, 62 Low, 3 Unknown)

The High findings are all the same `util-linux` family
(`util-linux`, `mount`, `login`, `libuuid1`, `libsmartcols1`, `libmount1`,
`liblastlog2-2`, `libblkid1`, `bsdutils`) and `perl-base`, which are pulled in
transitively by the Debian slim base image. At the time of the scan the
vulnerability database listed **no fixed version** for any of the 44 High
findings, so there is nothing to upgrade to yet.

### Frontend image — 161 findings (2 Critical, 41 High, 76 Medium, 42 Low)

The findings are in the Alpine base image and its runtime libraries
(`libssl3`/`libcrypto3`, `libexpat`, `libxml2`, `libpng`, `curl`, `zlib`,
`tiff`, `musl`, `nghttp2-libs`, `c-ares`). The single Critical CVE
(`CVE-2026-31789`, OpenSSL) affects both `libcrypto3` and `libssl3`, and a
fixed Alpine package (`3.3.3-r0` → `3.3.7-r0`) was already published, so it is
cleared by rebuilding on a refreshed base image.

### Why the counts look high

- Both base images carry a full OS userland that the application never
  exercises. The frontend image, for example, contains `curl`, `libxml2`, and
  image libraries that a static file server (nginx) does not use at runtime.
- The scan runs against the local base image digest; pinning to a fresh digest
  picks up the base image's own security updates.

### Remediation

1. Rebuild both images periodically (`make up` already does `--build`) so the
   base images pick up upstream fixes. This alone resolves the Critical OpenSSL
   finding.
2. For a hardened deployment, move to a distroless/static base image for the
   backend, or switch the frontend from `nginx:alpine` to
   `nginx:alpine-slim`/`caddy`, to shrink the unused OS surface.
3. Re-run `make security` after any base-image change and refresh the committed
   reports so the diff records the improvement.

## Scope and limitations

- Bandit is a static analyzer: it cannot see data-flow reachability, and these
  reports are a snapshot of one revision.
- Trivy reports the OS and language packages inside the images; the EFINGES
  application's own dependencies (FastAPI, SQLAlchemy, React, Vite) are part of
  that scan, and none of them appear in the High or Critical findings.
- The scans target the local images and the vulnerability database at scan
  time. Re-running later may legitimately produce different numbers, which is
  why the scan command is documented next to every report.
