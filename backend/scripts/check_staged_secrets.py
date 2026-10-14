"""Reject likely hard-coded credentials in staged additions."""

from __future__ import annotations

import re
import subprocess
import sys

SENSITIVE_ASSIGNMENT = re.compile(
    r"""\b(?:api[_-]?key|client[_-]?secret|password|passwd|secret[_-]?key|
        secret|access[_-]?token|auth[_-]?token|token|credential|credentials|
        bearer|private[_-]?key)\b\s*(?::\s*[A-Za-z_][\w.\[\] |,]*\s*)?[:=]\s*
        (?:"([^"]+)"|'([^']+)'|([^\s#]+))""",
    re.IGNORECASE | re.VERBOSE,
)
KNOWN_TOKEN = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16})\b")
PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
SAFE_VALUES = (
    "change-me",
    "changeme",
    "example",
    "placeholder",
    "replace",
    "test",
    "dummy",
    "dev-only",
)


def _looks_like_secret(line: str) -> bool:
    """Return whether an added line contains a likely credential."""
    if PRIVATE_KEY.search(line) or KNOWN_TOKEN.search(line):
        return True
    match = SENSITIVE_ASSIGNMENT.search(line)
    if match is None:
        return False
    value = next(value for value in match.groups() if value is not None).strip()
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower())
    is_placeholder = any(normalized.startswith(safe) for safe in SAFE_VALUES)
    return len(value) >= 12 and not is_placeholder


def staged_secret_findings(diff: str) -> list[str]:
    """Find likely secrets in added lines of a unified staged diff."""
    findings: list[str] = []
    path = "(unknown file)"
    line_number = 0
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
        elif line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)
            if match:
                line_number = int(match.group(1)) - 1
        elif line.startswith("+") and not line.startswith("+++"):
            line_number += 1
            if _looks_like_secret(line[1:]):
                findings.append(f"{path}:{line_number}: possible hard-coded credential")
        elif line.startswith(" "):
            line_number += 1
    return findings


def main() -> int:
    """Exit nonzero when the staged diff contains likely credentials."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--no-ext-diff", "--unified=0", "--"],
        check=True,
        capture_output=True,
        text=True,
    )
    findings = staged_secret_findings(result.stdout)
    if not findings:
        print("No likely hard-coded credentials found in staged additions.")
        return 0
    print("Refusing to commit likely hard-coded credentials:", file=sys.stderr)
    print("\n".join(findings), file=sys.stderr)
    print("Use environment variables or a non-secret placeholder.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
