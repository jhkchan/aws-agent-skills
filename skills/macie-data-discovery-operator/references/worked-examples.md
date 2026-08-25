# Macie Data Discovery Operator — worked examples (moved verbatim from SKILL.md)

> Progressive-disclosure split: this content was moved verbatim from SKILL.md; nothing was rewritten.

## Output format — literal template (secondary copy)

```text
OPERATION: <enable | classify | custom-id | findings | suppress | auto-discovery | security-hub | remediate | aggregate>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <macie-resource-name>
PRE_CHECKS:
  - [PASS|FAIL] <check description>
STEPS:
  1. CONFIRM: About to <operation> on <target>. Proceed? (yes/no)
  2. <exact CLI command with all flags populated>
POST_VERIFY:
  - [PASS|FAIL] <verification description>
STATE: <job status / finding state / Macie status>
NOTES: <detection coverage, severity, remediation caveats>
```

## Worked example — Macie not enabled (BLOCKED)

```text
OPERATION: classify
VERDICT: BLOCKED
TARGET: pii-scan-2026-08
PRE_CHECKS:
  - [FAIL] Macie session NOT ENABLED — get-macie-session returns
    NotFoundException. Macie must be enabled before creating
    classification jobs.
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
STATE: Macie disabled
NOTES: Enable Macie first: aws macie2 enable-macie-session --finding-publishing-frequency FIFTEEN_MINUTES --status ENABLED. For org-level, designate a delegated admin account via enable-organization-admin-account.
```

