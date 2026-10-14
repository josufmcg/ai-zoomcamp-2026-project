from scripts.check_staged_secrets import staged_secret_findings


def test_staged_secret_check_flags_sensitive_assignments_and_known_tokens() -> None:
    diff = "\n".join(
        [
            "diff --git a/config.py b/config.py",
            "+++ b/config.py",
            "@@ -0,0 +1,3 @@",
            "+" + 'password = "correct-horse-' + "battery-staple" + '"',
            "+" + 'token = "ghp_' + "123456789012345678901234567890" + '"',
            "+" + 'password: str = "type-annotated-' + "secretvalue" + '"',
        ]
    )

    findings = staged_secret_findings(diff)

    assert len(findings) == 3
    assert findings[0].startswith("config.py:1:")
    assert findings[1].startswith("config.py:2:")
    assert findings[2].startswith("config.py:3:")


def test_staged_secret_check_allows_documented_placeholders() -> None:
    diff = """\
diff --git a/config.py b/config.py
@@ -0,0 +1 @@
+SECRET_KEY = "dev-only-secret-key-change-me-in-production"
"""

    assert staged_secret_findings(diff) == []
