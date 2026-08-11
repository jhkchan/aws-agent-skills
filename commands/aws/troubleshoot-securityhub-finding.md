---
description: Diagnose and resolve AWS Security Hub findings through a standard-driven decision tree — collects service CLI (s3api, iam, ec2, kms, cloudtrail) corroborating evidence, identifies NOT_AVAILABLE StatusReasons and Resolved-but-still-failing races, applies Automation Rules and custom actions, and emits ROOT_CAUSE_FOUND with the specific control failure layer.
nl_triggers:
  - "Security Hub finding"
  - "Security Hub alert"
  - "troubleshoot Security Hub"
  - "Security Hub control failing"
  - "Security Hub NOT_AVAILABLE"
  - "Security Hub StatusReason"
  - "Security Hub stuck Resolved"
  - "Security Hub custom action"
  - "Security Hub Automation Rules"
  - "Security Hub custom control"
  - "Security Hub aggregator"
  - "Security Hub enabled standards"
  - "CIS control failed"
  - "PCI DSS control failed"
  - "FSBP control failed"
  - "Foundational Security Best Practices finding"
  - "NIST 800-53 control failed"
  - "S3.1 public access block"
  - "CIS.1.3 access key age"
  - "EC2.8 IMDSv2"
  - "KMS.3 key rotation"
  - "CloudTrail.4 data events"
  - "ASFF finding"
  - "Compliance.Status FAILED"
  - "Workflow.Status RESOLVED"
routes_to: securityhub-finding-troubleshooter
---

# /aws:troubleshoot-securityhub-finding

Activate the `securityhub-finding-troubleshooter` skill and diagnose a
Security Hub finding through the standard-driven decision tree.

## What it does

Reads a Security Hub finding (ASFF JSON or finding ID + account/region
for live lookup), then walks the standard-specific diagnostic tree to
the failed control with positive corroborating evidence:

1. **Pre-flight** — hub, enabled standards, aggregator, administrator
   (`describe-hub`, `describe-standards`, `get-finding-aggregator`,
   `get-administrator-account`), finding JSON (`get-findings`),
   Config rule backing the control (`describe-config-rules`).
   Short-circuits on missing context (NEED_MORE_INFO).
2. **Symptom entry** — map the control family to a branch:
   - **S3** (BPA, encryption, versioning, public ACL/policy) → Step 2.
   - **IAM** (password policy, MFA, access key age) → Step 3.
   - **EC2** (IMDSv2, security groups 0.0.0.0/0) → Step 4.
   - **KMS** (key rotation) → Step 5.
   - **CloudTrail** (data events, multi-region) → Step 6.
   - **Config** (recorder coverage) → Step 7.
   - **NOT_AVAILABLE** StatusReasons → Step 8.
   - **RESOLVED-but-still-appearing** race → Step 9.
   - **Cross-account aggregator** gap → Step 10.
   - **Custom action** wired but not firing → Step 11.
   - **Automation Rules** not applying → Step 12.
3. **Corroborating evidence** — for each branch, the canonical service
   probe: S3 → `s3api get-public-access-block / get-bucket-acl /
   get-bucket-encryption`; IAM → `iam get-account-password-policy /
   get-account-summary / get-credential-report`; EC2 → `ec2
   describe-instances.MetadataOptions / describe-security-groups`;
   KMS → `kms describe-keys.EnableKeyRotation`; CloudTrail →
   `cloudtrail describe-trails / get-event-selectors`. False-positive
   class tested explicitly.
4. **Verdict** — ROOT_CAUSE_FOUND (with failing resource confirmed by
   service probe), NEED_MORE_INFO (cross-account assume-role missing,
   Config recorder disabled), or ESCALATE (AWS-side Config rule Lambda
   crash, aggregator outage).
5. **Suppression / custom action** — for FALSE_POSITIVE, emit an
   Automation Rule JSON scoped to the resource/standard (NEVER
   blanket-suppress a control family). For true positives, recommend
   an EventBridge rule triggering Lambda (put-public-access-block,
   update-access-key, modify-instance-metadata-options,
   enable-key-rotation).

Emits a deterministic diagnostic block per finding:

```text
FINDING: <finding-id or control-id:resource>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
REASON: <1-2 sentences naming the control layer and the corroborating probe>
LAYER: <S3_BPA | IAM_PASSWORD_POLICY | IAM_MFA | EC2_IMDSV2 | EC2_SG |
        KMS_ROTATION | CLOUDTRAIL_DATA_EVENTS | CONFIG_RECORDER |
        CUSTOM_ACTION_GAPPED | STANDARD_DISABLED | AGGREGATOR_GAP |
        AUTOMATION_RULE_MISCONFIGURED | FALSE_POSITIVE | AWS_SIDE | UNKNOWN>
SEVERITY: <CRITICAL | HIGH | MEDIUM | LOW | INFORMATIONAL>
STANDARD: <CIS | PCI_DSS | FSBP | NIST_800_53 | CUSTOM>
EVIDENCE:
  - <Security Hub finding summary — control ID, resource, severity, compliance>
  - <corroborating probe — service CLI output>
  - <false-positive ruled out — name the FP class tested>
SUPPRESSION:
  - <if FALSE_POSITIVE: Automation Rules JSON>
  - <otherwise: "Not applicable — true control failure">
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification — usually aws securityhub get-findings re-check>
CONFIRM: Before any state-changing CLI, emit and await operator approval.
```

## When to invoke

Paste a Security Hub finding (JSON, finding ID, or control ID + resource)
and ask any of:

- "Investigate this S3.1 finding"
- "Why is my CIS.1.3 control NOT_AVAILABLE?"
- "EC2.8 keeps coming back as FAILED — why?"
- "Suppress recurring CIS.1.3 findings on the CI role"
- "Wire up EventBridge to auto-remediate S3.1 findings"
- "My aggregator is missing findings from the new member account"
- "Why isn't my Automation Rule firing on HIGH findings?"
- "Configure a custom control for our tagging policy"

A bare finding ID + account/region, or a pasted ASFF JSON, also routes
here via the orchestrator.

## Inputs

- Finding JSON (ASFF) or finding ID + account/region.
- For live investigation: standard ARN, control ID, resource ARN,
  cross-account assume-role (for member account queries).
- The skill uses `aws securityhub get-findings` /
  `get-findings-statistics` / `describe-standards` / `describe-hub` /
  `list-enabled-products-for-import` / `get-finding-aggregator` /
  `get-administrator-account` / `list-automation-rules` /
  `get-automation-rules` / `create-automation-rule` /
  `update-findings`, `aws configservice describe-config-rules` /
  `describe-configuration-recorders` /
  `get-resource-config-history` /
  `start-config-rules-evaluation`, `aws s3api
  get-public-access-block` / `get-bucket-acl` / `get-bucket-encryption`,
  `aws iam get-account-password-policy` / `get-account-summary` /
  `get-credential-report`, `aws ec2 describe-instances` /
  `describe-security-groups`, `aws kms describe-keys`, `aws cloudtrail
  describe-trails` / `get-event-selectors`, `aws events describe-rule`
  / `list-targets-by-rule` / `test-event-pattern`, `aws lambda
  get-policy`.

## Outputs

- One diagnostic block per finding with the LAYER value from the
  enumerated set.
- EVIDENCE section with the Security Hub summary AND a corroborating
  service probe (s3api / iam / ec2 / kms / cloudtrail) AND a named
  false-positive class that was ruled out — never a verdict without
  positive evidence.
- Suppression: Automation Rule JSON for FALSE_POSITIVE; custom action
  EventBridge pattern for auto-remediation of true positives.
- A CONFIRMATION gate precedes any state-changing CLI.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for Security Hub findings).
- `/aws:audit-securityhub-control` for Security Hub control compliance
  posture (FAILED/WARNING/PASSED scoring across the account).
- `/aws:troubleshoot-guardduty-finding` for threat-detection findings
  (GuardDuty, not Security Hub control failures).
- `/aws:audit-config-recorder-coverage` when the Config recorder is
  misconfigured and breaking Security Hub evaluations.
