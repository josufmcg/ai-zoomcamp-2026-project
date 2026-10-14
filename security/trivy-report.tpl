{{- /*
Compact, deterministic Trivy vulnerability template (backlog task 21).

Trivy's default `table` format wraps long titles to the detected terminal
width, so its output changes with the environment. This template emits one
tab-separated line per vulnerability instead, which makes the committed
reports stable and diff-friendly.

Usage:
    trivy image --scanners vuln --format template \
        --template '@security/trivy-report.tpl' <image>

Columns: CVE<TAB>SEVERITY<TAB>PACKAGE<TAB>INSTALLED<TAB>FIXED<TAB>TARGET<TAB>TITLE
*/ -}}
{{- range . -}}
{{- $target := .Target -}}
{{- range .Vulnerabilities -}}
{{ .VulnerabilityID }}	{{ .Severity }}	{{ .PkgName }}	{{ .InstalledVersion }}	{{ if .FixedVersion }}{{ .FixedVersion }}{{ else }}-{{ end }}	{{ $target }}	{{ .Title }}
{{ end -}}
{{ end -}}
