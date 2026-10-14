"""Guard the security and audit artifacts (backlog task 21).

These tests do not re-run the scanners (that needs ``bandit``/``trivy`` and the
built images); they check that the committed artifacts exist, stay in the
documented shape, and keep the properties the triage in ``security/README.md``
relies on. Re-run the scans with ``make security`` and then this test.
"""

from __future__ import annotations

import re
from pathlib import Path

# ``backend/tests/test_security_artifacts.py`` -> ``backend`` -> repository root.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SECURITY_DIR = REPOSITORY_ROOT / "security"

SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"}
TRIVY_COLUMNS = 7


def _read(path: Path) -> str:
    assert path.is_file(), f"missing security artifact: {path}"
    return path.read_text(encoding="utf-8")


def test_bandit_report_is_a_real_scan_of_the_backend_tooling() -> None:
    report = _read(SECURITY_DIR / "bandit-report.txt")

    assert report.startswith("Run started:")
    assert "Test results:" in report
    assert "Code scanned:" in report
    assert "Total lines of code:" in report


def test_bandit_report_has_no_findings_in_the_shipped_application() -> None:
    report = _read(SECURITY_DIR / "bandit-report.txt")

    # The triage in security/README.md claims app/ is clean; keep that true.
    locations = re.findall(r"Location: (\S+)", report)
    assert locations, "the report should list locations"
    assert not [location for location in locations if location.startswith("app/")]


def test_trivy_reports_are_tab_separated_and_severity_labelled() -> None:
    for name in ("trivy-backend.txt", "trivy-frontend.txt"):
        report = _read(SECURITY_DIR / name)
        rows = [line for line in report.splitlines() if line.strip()]

        assert rows, f"{name} should contain findings"
        for row in rows:
            # No ANSI colour codes: the template output must stay plain text.
            assert "\x1b[" not in row
            columns = row.split("\t")
            assert len(columns) == TRIVY_COLUMNS, f"{name}: {row!r}"
            cve, severity, package, installed, fixed, target, title = columns
            # CVE for the NVD identifiers, TEMP- for Debian placeholders, DSA-
            # for Debian security advisories, GHSA- for GitHub advisories.
            assert cve.startswith(("CVE-", "TEMP-", "DSA-", "GHSA-")), f"{name}: {cve!r}"
            assert severity in SEVERITIES, f"{name}: {severity!r}"
            assert package, f"{name}: empty package in {row!r}"
            assert installed, f"{name}: empty installed version in {row!r}"
            assert fixed, f"{name}: empty fixed field in {row!r}"
            assert target, f"{name}: empty target in {row!r}"
            assert title, f"{name}: empty title in {row!r}"


def test_trivy_template_and_triage_document_exist() -> None:
    template = _read(SECURITY_DIR / "trivy-report.tpl")
    assert "VulnerabilityID" in template
    assert "InstalledVersion" in template

    triage = _read(SECURITY_DIR / "README.md")
    for artifact in (
        "bandit-report.txt",
        "trivy-backend.txt",
        "trivy-frontend.txt",
        "trivy-report.tpl",
    ):
        assert artifact in triage


def test_pull_request_template_covers_the_review_checklist() -> None:
    template = _read(REPOSITORY_ROOT / ".github" / "pull_request_template.md")

    for marker in (
        "Backlog task",
        "prompt",
        "make openapi",
        "make test",
        "credential",
        "Alembic",
        "Reviewer sign-off",
    ):
        assert marker in template, f"pull request template is missing {marker!r}"


def test_operations_notes_cover_real_diagnosis_sessions() -> None:
    notes = _read(REPOSITORY_ROOT / "docs" / "operations.md")

    # Each entry starts with a "## N." heading; the task requires at least one,
    # and a symptom -> evidence -> root cause -> fix cycle per entry.
    sections = re.findall(r"^## \d+\.", notes, flags=re.MULTILINE)
    assert len(sections) >= 3

    for marker in ("Symptom.", "Root cause.", "Fix.", "Verification."):
        assert marker in notes, f"operations notes are missing {marker!r}"


def test_ai_policy_covers_prompting_privacy_and_review() -> None:
    policy = _read(REPOSITORY_ROOT / "docs" / "ai_policy.md")

    for marker in (
        "## 2. Prompt construction",
        "## 3. Data privacy",
        "## 5. Mandatory human review",
        "## 4. Permitted agent actions",
    ):
        assert marker in policy, f"ai_policy.md is missing {marker!r}"

    # The privacy section must name the secrets it forbids.
    assert "SECRET_KEY" in policy
    assert "credentials" in policy.lower()


def test_makefile_exposes_a_security_target() -> None:
    makefile = _read(REPOSITORY_ROOT / "Makefile")

    assert "security:" in makefile
    assert "bandit" in makefile
    assert "trivy" in makefile
    assert "bandit-report.txt" in makefile
    assert "trivy-backend.txt" in makefile
    assert "trivy-frontend.txt" in makefile
