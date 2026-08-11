---
description: Audit Amazon Macie data discovery and classification posture (Macie enablement, ASDD, classification job scoping, managed/custom data identifiers, suppression rule hygiene, multi-account delegation, Security Hub and EventBridge integration, sampling depth). Emits a CLASSIFIED, PARTIALLY_CLASSIFIED, or UNCLASSIFIED verdict with gap-cited checklist.
nl_triggers:
  - "audit macie"
  - "macie data classification"
  - "pii discovery coverage"
  - "macie job scoping"
  - "sensitive data s3 scan"
  - "custom data identifier review"
  - "macie security hub integration"
  - "macie multi-account"
  - "macie suppression rules"
  - "automated sensitive data discovery"
  - "macie findings filter"
  - "macie posture"
routes_to: macie-data-classifier
---

# /aws:audit-macie-data-classifier

Activate the `macie-data-classifier` skill and audit Amazon Macie
data discovery and classification posture.

## What it does

The skill walks the audit procedure and emits a CLASSIFIED,
PARTIALLY_CLASSIFIED, or UNCLASSIFIED checklist:

1. Macie enablement and finding frequency
2. Automated sensitive data discovery (ASDD) and auto-enable for members
3. Classification jobs and scoping (bucket inclusion/exclusion patterns)
4. Managed data identifiers (ALL vs RECOMMENDED vs PARTIAL)
5. Custom data identifiers (regex quality scoring)
6. Finding types and severities (High/Medium/Low distribution)
7. Suppression rules (SUPPRESS vs ARCHIVE, scope review)
8. Multi-account topology (administrator/member, effective coverage)
9. Security Hub and CloudWatch Events integration
10. Sampling depth vs full-scan trade-off for high-sensitivity buckets
11. Recent features (ASDD improvements, Audit Manager integration)

## When to use

- You need to audit Macie data classification coverage.
- You want to verify PII detection posture across S3 buckets.
- You need to validate classification job scoping (coverage gaps).
- You want to review suppression rule hygiene (broad suppression masking).
- You need to check multi-account Macie delegation completeness.
- You want to verify Security Hub integration is active.
- You want to assess custom identifier regex quality.

## When NOT to use

- **Operating Macie jobs** (enable, create, suppress) — use macie-data-
  discovery-operator.
- **Provisioning Macie resources** — use deploy/operate skills.
- **Auditing non-Macie security services** — use the relevant service
  auditor.

## How to invoke

### Slash command

```
/aws:audit-macie-data-classifier
```

Then provide: target account(s), Region(s), Macie enablement status,
ASDD status, classification job list, custom identifier details,
suppression rule list, multi-account member status, Security Hub
integration status.

### Natural language

Any of these routes to the same skill:

- "audit Macie data classification for account 123456789012"
- "review PII discovery coverage in my S3 estate"
- "check if my Macie suppression rules are masking findings"
- "verify Macie multi-account coverage across my organization"
- "assess my custom data identifier regex quality"

### CLI routing

```bash
node cli/bin/cli.js route "audit macie data classification"
```

## Pipeline integration

This skill operates in **Phase 2 (Audit)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to assess Macie
classification posture. The output checklist feeds into compliance
reporting and downstream remediation skills.

## Example

```
You: /aws:audit-macie-data-classifier

     Audit the Macie posture for account 123456789012 in
     us-east-1. Macie is enabled. ASDD is enabled. 2 jobs
     (both one-time). 1 custom identifier with regex \d{1,19}.
     Security Hub export is disabled.

Skill:
  MACIE_CLASSIFICATION: 123456789012 (us-east-1) — ENABLED
  VERDICT: PARTIALLY_CLASSIFIED
  CHECKLIST:
    [✓] Macie session: ENABLED
    [✓] ASDD: ENABLED
    [✗] Classification jobs: 2 (one-time: 2, scheduled: 0)
    [✗] Custom identifiers: 1 (scored: 0/0/1 — high risk)
    [✗] Security Hub export: DISABLED
  VERIFICATION_COMMANDS:
    aws macie2 get-macie-session --region us-east-1
    aws macie2 list-classification-jobs --region us-east-1
```

## References

- Skill definition: `skills/macie-data-classifier/SKILL.md`
- Job scoping and identifiers guide: `skills/macie-data-classifier/references/job-scoping-and-identifiers.md`
- Multi-account and findings routing guide: `skills/macie-data-classifier/references/multi-account-and-findings-routing.md`
- Eval suite: `skills/macie-data-classifier/evals/evals.json`
