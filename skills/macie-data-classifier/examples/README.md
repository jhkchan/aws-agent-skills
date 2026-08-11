# End-to-End Example: Macie Data Classification Audit

A walkthrough showing how to use the `macie-data-classifier` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are auditing the Macie data classification posture for an
organization with administrator account 123456789012 in us-east-1.
The audit needs to verify:

- Macie is enabled with appropriate finding frequency
- ASDD is enabled with org-wide auto-enable
- Classification jobs cover all high-sensitivity buckets
- Custom identifiers have healthy regex quality
- Suppression rules are narrow (not masking High severity)
- Security Hub export is enabled
- EventBridge rule is active for automated response
- Multi-account coverage is complete (148/150 accounts)

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:audit-macie-data-classifier
```

Then paste the Macie posture details.

### Option B: Natural language

```
You: "Audit the Macie data classification posture for account
      123456789012 in us-east-1. Macie is enabled, ASDD is on,
      4 jobs scoping 28 sensitive buckets, 3 custom identifiers,
      148/150 org accounts enrolled, Security Hub export enabled."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "audit macie data classification"
```

---

## Step 2 — Skill produces the CLASSIFIED checklist

```text
MACIE_CLASSIFICATION: 123456789012 (us-east-1) — ENABLED
VERDICT: CLASSIFIED
CHECKLIST:
  [✓] Macie session: ENABLED
  [✓] Finding frequency: FIFTEEN_MINUTES
  [✓] Automated discovery (ASDD): ENABLED
  [✓] ASDD auto-enable members: true
  [✓] Classification jobs: 4 (one-time: 1, scheduled: 3)
  [✓] Job scoping: 28 sensitive buckets included, 12 non-sensitive excluded
  [✓] Coverage gap: 120 total buckets, 108 ASDD, 28 deep-scan, 12 unmonitored (low-risk)
  [✓] Managed identifiers: ALL
  [✓] Custom identifiers: 3 (scored: 3/0/0 — all healthy)
  [✓] High-sensitivity deep-scan: 12/12 buckets with full-scan scheduled jobs (daily)
  [✓] Findings (last 30d): 2 High (triaged), 8 Medium, 15 Low (archived)
  [✓] Suppression rules: 4 (SUPPRESS: 1, ARCHIVE: 3)
  [✓] Suppression scope: narrow (1 SUPPRESS for known-public-bucket, no High severity suppressed)
  [✓] Multi-account: 148/150 accounts enrolled (2 pending invitation)
  [✓] Security Hub export: ENABLED
  [✓] EventBridge rule: active (target: macie-auto-remediation Lambda)
  [✓] Sampling depth: high-sensitivity full-scan
  [✓] Tags: Environment=production, Compliance=PCI-DSS
VERIFICATION_COMMANDS:
  aws macie2 get-macie-session --region us-east-1
  aws macie2 get-automated-discovery-configuration --region us-east-1
  aws macie2 list-classification-jobs --region us-east-1
  aws macie2 list-findings-filters --region us-east-1
  aws macie2 list-members --region us-east-1
```

---

## Step 3 — Audit verification commands

```bash
# Verify Macie session and finding frequency
aws macie2 get-macie-session --region us-east-1 \
  --query '{Status:status,Frequency:findingPublishingFrequency}'

# Verify ASDD configuration
aws macie2 get-automated-discovery-configuration --region us-east-1 \
  --query '{Status:status,AutoEnable:autoEnableOrganizationMembers}'

# List classification jobs and verify scoping
aws macie2 list-classification-jobs --region us-east-1 \
  --query 'items[*].{Name:name,Status:jobStatus,Type:jobType}' \
  --output table

# Inspect a specific job's scoping
JOB_ID="daily-pii-scan"
aws macie2 describe-classification-job --job-id "$JOB_ID" --region us-east-1 \
  --query '{Name:name,Type:jobType,Status:jobStatus,Scoping:s3JobDefinition.scoping,Sample:sampleDeep}'

# Verify custom identifiers
aws macie2 list-custom-data-identifiers --region us-east-1 \
  --query 'customDataIdentifiers[*].{Name:name,Id:id}' \
  --output table

# Review suppression rules
aws macie2 list-findings-filters --region us-east-1 \
  --query 'findingsFilterIds[*].{Name:name,Action:action}' \
  --output table

# Verify multi-account coverage
aws macie2 list-members --region us-east-1 \
  --query 'members[*].{AccountId:accountId,Status:relationshipStatus}' \
  --output table

# Verify Security Hub integration
aws securityhub get-findings \
  --filters '{"ProductName":[{"Value":"Macie","Comparison":"EQUALS"}]}' \
  --region us-east-1 --query 'Findings[*].{Id:Id,Severity:Severity.Severity}' \
  --output table | head -10

# Verify EventBridge rule
aws events list-rules --region us-east-1 \
  --query 'Rules[?contains(EventPattern,`Macie Finding`)].{Name:Name,State:State}' \
  --output table
```

---

## What the skill catches that a naive audit misses

| Configuration | Naive audit | Skill output | Why the skill is right |
|---|---|---|---|
| ASDD vs job coverage | "ASDD enabled → covered" | Coverage gap: 120 buckets, 108 ASDD, 28 deep-scan, 12 unmonitored | ASDD samples objects; jobs deep-scan. The gap matters. |
| Custom identifier regex | Counts identifiers | Scores regex quality: 3/0/0 (all healthy) | Bad regex causes timeouts and false-positive floods |
| Suppression rules | Checks they exist | Reviews scope: narrow vs BROAD, flags SUPPRESS on High severity | Broad suppression masks real findings |
| Sampling depth | Not checked | High-sensitivity full-scan: 12/12 buckets | ASDD-only is insufficient for high-sensitivity |
| Multi-account | "Members exist" | Effective coverage: 148/150 (2 pending) | INVITED/PAUSED members are not scanned |
| Security Hub | Not verified | Export: ENABLED | Export is per-Region, must be explicitly enabled |

---

## Related artifacts

- **Skill definition:** `skills/macie-data-classifier/SKILL.md`
- **Job scoping and identifiers guide:** `skills/macie-data-classifier/references/job-scoping-and-identifiers.md`
- **Multi-account and findings routing guide:** `skills/macie-data-classifier/references/multi-account-and-findings-routing.md`
- **Slash command:** `commands/aws/audit-macie-data-classifier.md`
- **Eval suite:** `skills/macie-data-classifier/evals/evals.json`
- **Legacy test cases:** `skills/macie-data-classifier/eval/test-cases.yaml`
