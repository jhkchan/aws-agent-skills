---
description: >-
  Audit Amazon Inspector2 coverage gaps and finding severity for EC2, ECR, and
  Lambda resources. Emits a CRITICAL / HIGH / MEDIUM / LOW / COVERED verdict
  per resource by reasoning over coverage state, network reachability, CISA
  KEV catalog, and finding lifecycle.
nl_triggers:
  - "inspector2 coverage gap"
  - "are my EC2 instances scanned"
  - "vulnerability scan coverage"
  - "inspector finding severity"
  - "is this resource covered by inspector"
  - "CVE reachability"
  - "network reachable vulnerability"
  - "ECR scanOnPush audit"
  - "Lambda code scanning"
  - "SSM agent inspector coverage"
  - "KEV catalog check"
  - "vulnerability posture audit"
  - "inspector2 findings review"
  - "scan coverage audit"
routes_to: inspector2-coverage-finding-auditor
---

# /aws:audit-inspector2-coverage-findings

Activate the `inspector2-coverage-finding-auditor` skill and audit Inspector2
coverage gaps and finding severity for one or more resources.

## What it does

Reads Inspector2 account status, per-resource coverage data, and finding
records, then applies the 8-step classification logic in declaration order:

0. Validate input + check Inspector2 account-level enablement (EC2 / ECR /
   Lambda / Lambda-code scanning status).
1. Per-resource coverage assessment (SSM-agent dependency for EC2,
   scanOnPush + freshness for ECR, code-scanning opt-in for Lambda).
2. Coverage gap severity by resource tier (production/sensitive vs standard).
3. Finding filter — only OPEN findings count (SUPPRESSED/CLOSED excluded,
   INFORMATIONAL does not escalate).
4. Finding severity with reachability amplification (internet-reachable CVE
   escalates one level; CISA KEV catalog escalates to CRITICAL).
5. Finding type taxonomy (PACKAGE / CODE / NETWORK / MISCONFIG).
6. Resource-level aggregation — worst of coverage gap + finding severity.
7. Account/region-level aggregation — worst across all resources.

Emits a deterministic VERDICT per resource:

```text
RESOURCE: <type/name-or-id>
VERDICT: CRITICAL | HIGH | MEDIUM | LOW | COVERED
REASON: <1-2 sentences citing the specific finding or coverage gap and the rule that fired>
COVERAGE: ACTIVE | STALE_MODERATE | STALE_SEVERE | UNCOVERED | PARTIAL
FINDINGS: <count> OPEN (<N> CRITICAL, <N> HIGH, <N> MEDIUM, <N> LOW, <N> INFORMATIONAL)
REMEDIATION: <specific action, or "None required" if COVERED>
```

## When to invoke

Paste Inspector2 coverage/finding data and ask any of:

- "are my EC2 instances covered by Inspector2?"
- "what's the severity of these findings?"
- "is this CVE internet-reachable?"
- "check scan coverage before production deployment"
- "which findings should I prioritize?"

A bare resource name + any audit verb ("audit this instance's coverage",
"check ECR scanOnPush") also routes here via the orchestrator.

## Inputs

- Inspector2 account status (`batch-get-account-status` output).
- Per-resource coverage data (`list-coverage` output).
- Finding records (`list-findings` output, filtered to status=OPEN).
- Optional: resource tags (env, critical, compliance) for tier classification.
- Optional: SSM instance information for EC2 coverage validation.

## Outputs

- One VERDICT block per resource.
- For multi-resource audits: an account/region summary with per-resource
  breakdown and the aggregate verdict (worst across all resources).
- Specific remediation per verdict: containment-first for internet-reachable
  CRITICAL, coverage re-enrollment for gaps, patch guidance for CVEs.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the Phase 2
  Audit specialist for vulnerability-management coverage).
- `/aws:audit-ec2-security-groups` for network-exposure deep-analysis when a
  NETWORK_REACHABILITY finding indicates a security-group issue.
- `/aws:audit-iam-least-privilege` for privilege-escalation context on
  MISCONFIGURATION findings.
