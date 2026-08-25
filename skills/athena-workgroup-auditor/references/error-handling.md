# Error Handling — Athena Workgroup Auditor

Load-on-demand error handling moved verbatim from SKILL.md.

## Malformed Configuration JSON — ERROR verdict block


```text
WORKGROUP: <name>
VERDICT: ERROR
REASON: Workgroup Configuration block is not valid JSON or is missing required fields — cannot classify.
REMEDIATION: Retrieve the canonical config with `aws athena get-work-group --work-group <name> --output json` and re-audit.
```
