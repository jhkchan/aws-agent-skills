# End-to-End Example: Security Hub Control Compliance Audit

A walkthrough showing how to use the `securityhub-control-compliance-auditor`
skill from invocation through remediation. Mirrors the structured-eval pattern of
shipping a concrete worked example per skill.

---

## Scenario

You are preparing for a quarterly compliance review and need to triage 5
Security Hub findings across different controls and lifecycle states. The
findings are:

1. **S3.2** — Bucket-level BPA on `app-uploads-prod` (active FAILED, NEW).
2. **IAM.7** — Password policy (PASSED, previously RESOLVED).
3. **Redshift.1** — Redshift public access (NOT_AVAILABLE, NO_RESOURCES).
4. **Config.1** — AWS Config enabled (NOT_AVAILABLE, Config not enabled in
   eu-west-2).
5. **EC2.15** — Security group 0.0.0.0/0 on admin port (FAILED but
   SUPPRESSED).

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:audit-securityhub-control-compliance
```

Then paste the five finding JSONs.

### Option B: Natural language

```
You: "Triage these Security Hub findings for our quarterly compliance review:

  Finding 1 — S3.2 (app-uploads-prod):
    Compliance.Status: FAILED, Workflow: NEW, RecordState: ACTIVE

  Finding 2 — IAM.7:
    Compliance.Status: PASSED, Workflow: RESOLVED, RecordState: ACTIVE

  Finding 3 — Redshift.1:
    Compliance.Status: NOT_AVAILABLE, StatusReasons: NO_RESOURCES

  Finding 4 — Config.1 (eu-west-2):
    Compliance.Status: NOT_AVAILABLE,
    StatusReasons: SUPPORTED_SERVICE_NOT_ENABLED

  Finding 5 — EC2.15 (sg-0abc123):
    Compliance.Status: FAILED, Workflow: SUPPRESSED,
    RecordState: ACTIVE
"
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "audit security hub control compliance"
# [Phase: Audit | Skills routed: securityhub-control-compliance-auditor]
```

---

## Step 2 — Skill produces deterministic verdicts

The skill applies its classification logic in order (ARCHIVED -> SUPPRESSED
-> RESOLVED -> NOT_AVAILABLE split -> FAILED -> WARNING -> PASSED) and emits
a per-finding report:

```text
CONTROL: S3.2 (S3 Bucket-Level Public Access Prohibition)
VERDICT: FAILED
REASON: Rule 5 (active FAILED) — Compliance.Status is FAILED,
        Workflow.Status is NEW, RecordState is ACTIVE. The bucket
        app-uploads-prod does not have bucket-level BPA enabled.
SEVERITY: HIGH
REMEDIATION: Enable all 4 bucket-level BPA settings on app-uploads-prod:
  aws s3api put-public-access-block --bucket app-uploads-prod
    --public-access-block-configuration
      BlockPublicAcls=true,IgnorePublicAcls=true,
      BlockPublicPolicy=true,RestrictPublicBuckets=true

CONTROL: IAM.7 (IAM Password Policy)
VERDICT: PASSED
REASON: Rule 7 (PASSED) — Compliance.Status is PASSED, RecordState is
        ACTIVE. The account password policy meets all FSBP requirements.
SEVERITY: MEDIUM
REMEDIATION: None required.

CONTROL: Redshift.1 (Redshift Clusters Public Access)
VERDICT: NOT_APPLICABLE
REASON: Rule 4 (NOT_AVAILABLE — NO_RESOURCES) — Compliance.Status is
        NOT_AVAILABLE with StatusReasons code NO_RESOURCES. No Redshift
        clusters exist in this account/region. The control does not apply.
SEVERITY: —
REMEDIATION: None required — control does not apply.

CONTROL: Config.1 (AWS Config Enabled)
VERDICT: WARNING
REASON: Rule 4 (NOT_AVAILABLE — SUPPORTED_SERVICE_NOT_ENABLED) —
        Compliance.Status is NOT_AVAILABLE with StatusReasons code
        SUPPORTED_SERVICE_NOT_ENABLED. AWS Config is not enabled in
        eu-west-2, so this control cannot evaluate. This is a monitoring
        posture gap, not a pass.
SEVERITY: MEDIUM
REMEDIATION: Enable AWS Config in eu-west-2:
  aws configservice put-configuration-recorder
    --configuration-recorder name=default,roleARN=<config-role>
    --recording-group allSupported=true,includeGlobalResourceTypes=true

CONTROL: EC2.15 (EC2 Security Group 0.0.0.0/0 on Admin Port)
VERDICT: WARNING
REASON: Rule 2 (suppressed FAILED — governance concern) —
        Compliance.Status is FAILED but Workflow.Status is SUPPRESSED.
        The control is still failing; the finding was hidden from the
        default dashboard view. No Workflow.Note is present — the
        suppression lacks a documented justification. FirstObservedAt is
        2026-06-01 (>60 days ago) — the suppression may be stale.
SEVERITY: HIGH
REMEDIATION: Review the suppression. If the compensating control is no
             longer valid, unsuppress the finding and apply the FAILED
             remediation path (restrict the SG rule to a known CIDR):
  aws ec2 revoke-security-group-ingress --group-id sg-0abc123
    --ip-permissions IpProtocol=tcp,FromPort=22,ToPort=22,IpRanges=[{CidrIp=0.0.0.0/0}]
  aws ec2 authorize-security-group-ingress --group-id sg-0abc123
    --ip-permissions IpProtocol=tcp,FromPort=22,ToPort=22,IpRanges=[{CidrIp=10.0.0.0/8}]

AGGREGATE VERDICT: FAILED
BREAKDOWN: 1 FAILED, 2 WARNING, 1 PASSED, 1 NOT_APPLICABLE
```

---

## Step 3 — Pipeline integration (Prioritize + Remediate)

When invoked through the orchestrator (`/aws:pipeline`), the findings flow
into the Prioritize and Remediate phases:

```
[Phase: Prioritize | Findings: 1 HIGH FAILED, 1 MEDIUM WARNING, 1 HIGH WARNING | Skills routed: orchestrator]

1. HIGH/FAILED: S3.2 — bucket-level BPA not set on app-uploads-prod
   (active exposure — bucket may accept public ACLs/policies)
2. HIGH/WARNING: EC2.15 — suppressed FAILED on sg-0abc123
   (0.0.0.0/0 on admin port, suppressed without justification >60 days)
3. MEDIUM/WARNING: Config.1 — AWS Config not enabled in eu-west-2
   (monitoring blind spot — all eu-west-2 controls are NOT_AVAILABLE)
4. —: IAM.7 PASSED, Redshift.1 NOT_APPLICABLE (no action)
```

---

## Step 4 — Post-remediation verification

After applying fixes and waiting for the Security Hub re-evaluation cycle
(12-24 hours), re-run the audit. Expected output:

```text
CONTROL: S3.2
VERDICT: PASSED
REASON: Rule 7 (PASSED) — Compliance.Status is PASSED. Bucket-level BPA
        is now enabled on app-uploads-prod.
REMEDIATION: None required.

CONTROL: EC2.15
VERDICT: PASSED
REASON: Rule 7 (PASSED) — Compliance.Status is PASSED after unsuppression
        and SG rule restriction. Workflow.Status is RESOLVED.
REMEDIATION: None required.

CONTROL: Config.1
VERDICT: PASSED
REASON: Rule 7 (PASSED) — AWS Config now enabled in eu-west-2. Control
        evaluates successfully.
REMEDIATION: None required.
```

---

## What the skill catches that a naive review misses

| Finding | Naive review | Skill verdict | Why the skill is right |
|---|---|---|---|
| S3.2 | "FAILED — enable BPA" | FAILED | Correct, but the skill also maps to the exact CLI command and cites Rule 5. |
| IAM.7 | "PASSED — all good" | PASSED | Correct, but the skill notes Workflow.Status = RESOLVED (was previously failing) — useful lifecycle context. |
| Redshift.1 | "NOT_AVAILABLE — can't tell" | NOT_APPLICABLE | The skill checks StatusReasons: NO_RESOURCES means the control genuinely doesn't apply. No action needed. |
| Config.1 | "NOT_AVAILABLE — probably fine" | WARNING | The skill catches that SUPPORTED_SERVICE_NOT_ENABLED means AWS Config is OFF — a monitoring gap. Every eu-west-2 control is unevaluable. This is a WARNING, not a pass. |
| EC2.15 | "SUPPRESSED — already handled" | WARNING | The most dangerous misclassification. A naive review sees "suppressed" and moves on. The skill recognizes that a SUPPRESSED FAILED means the control is still failing — the finding was hidden, not fixed. No suppression note + >60 days old = stale suppression. |

---

## Related artifacts

- **Skill definition:** `skills/securityhub-control-compliance-auditor/SKILL.md`
- **Slash command:** `commands/aws/audit-securityhub-control-compliance.md`
- **Eval suite:** `skills/securityhub-control-compliance-auditor/evals/evals.json`
- **Legacy test cases:** `skills/securityhub-control-compliance-auditor/eval/test-cases.yaml`
