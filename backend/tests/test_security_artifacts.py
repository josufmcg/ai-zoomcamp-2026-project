"""Guard the security and audit artifacts (backlog task 21).

These tests do not re-run the scanners (that needs ``bandit``/``trivy`` and the
built images); they check that the committed artifacts exist, stay in the
documented shape, and keep the properties the triage in ``security/README.md``
relies on. Re-run the scans with ``make security`` and then this test.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

# ``backend/tests/test_security_artifacts.py`` -> ``backend`` -> repository root.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SECURITY_DIR = REPOSITORY_ROOT / "security"
PR_AUDITS_DIR = REPOSITORY_ROOT / "docs" / "pr_audits"

# The section headings from ``.github/pull_request_template.md`` that every
# completed audit must carry, so an audit is the template actually applied.
AUDIT_SECTIONS = (
    "## Summary",
    "## Provenance (AI-assisted work)",
    "## Correctness and tests",
    "## API contract",
    "## Security and privacy",
    "## Database",
    "## Documentation",
)

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


def test_completed_pr_audits_apply_the_review_checklist() -> None:
    """The evaluation asks for PR audit output, not only a blank template."""

    audits = sorted(PR_AUDITS_DIR.glob("task-*.md"))
    assert audits, "docs/pr_audits/ should hold at least one completed audit"

    for audit in audits:
        text = _read(audit)
        for section in AUDIT_SECTIONS:
            assert section in text, f"{audit.name} is missing section {section!r}"
        # A completed audit states a verdict and is signed off by a reviewer.
        assert "Verdict:" in text, f"{audit.name} has no verdict"
        assert "Reviewer sign-off:" in text, f"{audit.name} is not signed off"

    index = _read(PR_AUDITS_DIR / "README.md")
    assert "pull_request_template.md" in index
    for audit in audits:
        assert audit.name in index, f"docs/pr_audits/README.md does not list {audit.name}"


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


def test_ai_workflow_record_covers_prompts_context_and_verification() -> None:
    workflow = _read(REPOSITORY_ROOT / "docs" / "ai_workflow.md")

    for marker in (
        "## 3. Worked examples per phase",
        "## 4. Verification evidence",
    ):
        assert marker in workflow, f"ai_workflow.md is missing {marker!r}"

    # The record must name the reusable delegation templates and the context
    # files the model is given, so a change can be reproduced.
    for marker in (
        "AGENTS.md",
        "docs/specs.md",
        "docs/architecture.md",
        "implement-backlog-task.prompt.md",
        "make openapi",
    ):
        assert marker in workflow, f"ai_workflow.md is missing {marker!r}"

    # Every phase must carry a concrete example (prompt -> result -> correction).
    assert workflow.count("**Correction") >= 5


def test_makefile_exposes_a_security_target() -> None:
    makefile = _read(REPOSITORY_ROOT / "Makefile")

    assert "security:" in makefile
    assert "bandit" in makefile
    assert "trivy" in makefile
    assert "bandit-report.txt" in makefile
    assert "trivy-backend.txt" in makefile
    assert "trivy-frontend.txt" in makefile


def test_ci_workflow_tests_and_deploys_the_stack() -> None:
    """The evaluation's CI/CD tier wants tests *and* a deploy when they pass."""

    workflow = yaml.safe_load(
        (REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    )
    jobs = workflow["jobs"]

    for job in ("backend", "frontend"):
        assert job in jobs, f"ci.yml is missing the {job!r} job"

    # A deploy job must exist and must actually run the deployed stack, not just
    # build an image: bring the compose stack up, wait for health, and probe the
    # live endpoints.
    deploy = jobs.get("deploy")
    assert deploy is not None, "ci.yml has no deploy job"
    assert "backend" in deploy["needs"] and "frontend" in deploy["needs"]

    steps = "\n".join(step.get("run", "") for step in deploy["steps"])
    assert "docker compose up" in steps
    assert "--wait" in steps
    assert "/healthz" in steps
    # Deploying proves the deployed database works: seed and read it back.
    assert "make seed" in steps
    assert "/auth/token" in steps and "/bills" in steps
