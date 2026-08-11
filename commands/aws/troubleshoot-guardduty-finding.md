---
description: Investigate Amazon GuardDuty findings through a finding-type-driven diagnostic tree — collects CloudTrail, VPC Flow Log, and CloudWatch corroborating evidence, identifies false positives, applies suppression via create-filter, and emits ROOT_CAUSE_FOUND with the specific threat layer (credential abuse, crypto mining, IAM persistence, exfiltration, runtime anomaly).
nl_triggers:
  - "GuardDuty finding"
  - "GuardDuty alert"
  - "investigate GuardDuty"
  - "GuardDuty triage"
  - "Recon:IAMUser"
  - "Recon:EC2/PortProbe"
  - "UnauthorizedAccess:IAMUser"
  - "UnauthorizedAccess:EC2/SSHBruteForce"
  - "UnauthorizedAccess:EC2/RDPBruteForce"
  - "Backdoor:EC2"
  - "Backdoor:EC2/C&CActivity"
  - "CryptoCurrency:EC2"
  - "CryptoCurrency:EC2/BitcoinTool"
  - "Persistence:IAMUser"
  - "Persistence:IAMUser/UserCreation"
  - "Policy:IAMUser"
  - "Policy:IAMUser/S3BucketAnonymousGranted"
  - "Exfiltration:S3"
  - "Exfiltration:EC2"
  - "Runtime:EC2/ProcessA"
  - "Runtime:ECS/ProcessA"
  - "Runtime:EKS/ProcessA"
  - "GuardDuty Runtime Monitoring"
  - "EKS Protection finding"
  - "Malware Protection scan"
  - "GuardDuty false positive"
  - "GuardDuty suppression filter"
  - "isolate EC2 from GuardDuty"
  - "quarantine EC2 GuardDuty"
  - "revoke IAM credentials GuardDuty"
routes_to: guardduty-finding-investigator
---

# /aws:troubleshoot-guardduty-finding

Activate the `guardduty-finding-investigator` skill and investigate a
GuardDuty finding through the finding-type-driven diagnostic tree.

## What it does

Reads a GuardDuty finding JSON (or finding ID + detector ID for live
lookup), then walks the finding-type-specific diagnostic tree to a root
cause with positive corroborating evidence:

1. **Pre-flight** — detector ID and feature enablement (`list-detectors`,
   `list-features`), finding JSON (`get-findings`), trusted IP list
   (`list-ip-sets`), VPC Flow Log location, CloudTrail lookup window.
   Short-circuits on missing context (NEED_MORE_INFO).
2. **Symptom entry** — map the finding-type family to a branch:
   - **Recon** (port probes, IAM UserPermissions) → Step 2.
   - **UnauthorizedAccess** (ConsoleLogin new geo, SSH/RDP brute force)
     → Step 3.
   - **Backdoor** (C&C, spambot) → Step 4.
   - **CryptoCurrency** (BitcoinTool.B / BitcoinTool.B!DNS) → Step 5.
   - **Persistence** (UserCreation, IAMUser anomaly) → Step 6.
   - **Policy** (S3BucketAnonymousGranted, RootCredentialUsage) → Step 7.
   - **Exfiltration** (S3 anomalous GetObject, EC2 PortSweep) → Step 8.
   - **Runtime** (Runtime:EC2/ECS/EKS/ProcessA) → Step 9.
   - Malware Protection scan needed → Step 10.
3. **Corroborating evidence** — for each branch, the canonical probe:
   IAM findings → CloudTrail `lookup-events` (actor, source IP,
   MFAUsed); network findings → VPC Flow Logs (egress to suspicious
   CIDRs); runtime findings → CloudWatch Container Insights +
   `service.runtimeData`. False-positive class tested explicitly.
4. **Verdict** — ROOT_CAUSE_FOUND (with failing probe that corroborates
   the threat), NEED_MORE_INFO (VPC Flow Logs not enabled, CloudTrail
   data events off, agent missing), or ESCALATE (AWS-side incident,
   APT indicators, regulated-data exfil).
5. **Suppression / auto-remediation** — for FALSE_POSITIVE, emit a
   `create-filter` JSON scoped to the resource/actor/API (NEVER
   blanket-suppress a finding family); prefer the trusted IP list for
   known-benign sources. For High-severity true positives, recommend an
   EventBridge rule triggering Lambda (isolate EC2 SG, deactivate IAM
   access key, trigger Malware Protection scan).

Emits a deterministic diagnostic block per finding:

```text
FINDING: <finding-id or finding-type:resource>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
REASON: <1-2 sentences naming the threat layer and the corroborating evidence>
LAYER: <CREDENTIAL_ABUSE | CRYPTO_MINING | SSH_BRUTE_FORCE | IAM_PERSISTENCE |
        POLICY_CHANGE | DATA_EXFILTRATION | RUNTIME_ANOMALY | FALSE_POSITIVE |
        SUPPRESSED | AWS_SIDE | UNKNOWN>
SEVERITY: <LOW | MEDIUM | HIGH>
EVIDENCE:
  - <GuardDuty finding summary — type, resource, actor, severity>
  - <corroborating probe — CloudTrail / VPC Flow / CloudWatch>
  - <false-positive ruled out — name the FP class tested>
SUPPRESSION:
  - <if FALSE_POSITIVE: create-filter JSON for archive rule>
  - <otherwise: "Not applicable — true positive">
REMEDIATION:
  1. <containment action with CLI command>
  2. <verification command after containment>
CONFIRM: Before any state-changing CLI, emit and await operator approval.
```

## When to invoke

Paste a GuardDuty finding (JSON, finding ID, or finding-type family +
resource) and ask any of:

- "Investigate this GuardDuty finding"
- "Is this CryptoCurrency finding a false positive?"
- "Triage this ConsoleLogin from a new country"
- "My EC2 instance triggered Backdoor:EC2/C&CActivity.B — help"
- "What should I do for a Persistence:IAMUser finding?"
- "Suppress recurring Recon:EC2/PortProbe from our scanner"
- "Trigger Malware Protection scan on this snapshot"
- "Wire up EventBridge to auto-isolate High-severity GuardDuty findings"

A bare finding ID + detector ID, or a pasted finding JSON, also routes
here via the orchestrator.

## Inputs

- Finding JSON or finding ID + detector ID (region).
- For live investigation: time window, VPC Flow Log group/S3,
  CloudTrail trail, IAM user, instance ID, EKS cluster name.
- The skill uses `aws guardduty get-findings` /
  `get-findings-statistics` / `list-ip-sets` / `list-features`,
  `aws cloudtrail lookup-events`, `aws ec2 describe-flow-logs`,
  `aws logs start-query / filter-log-events / get-query-results`,
  `aws ec2 describe-instances`, `aws ec2 describe-security-groups`,
  `aws iam get-access-key-last-used`, `aws s3api get-bucket-acl` /
  `get-bucket-logging`, `aws malware-scan start-malware-scan` /
  `list-scans` / `get-scan`.

## Outputs

- One diagnostic block per finding with the LAYER value from the
  enumerated set.
- EVIDENCE section with the GuardDuty summary AND a corroborating probe
  (CloudTrail event, VPC Flow record, CloudWatch metric) AND a named
  false-positive class that was ruled out — never a verdict without
  positive evidence.
- Suppression: `create-filter` JSON for FALSE_POSITIVE; trusted IP list
  recommendation for known-benign CIDRs; auto-remediation EventBridge
  pattern for High-severity true positives.
- A CONFIRMATION gate precedes any state-changing CLI.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for GuardDuty findings).
- `/aws:audit-guardduty-findings` for GuardDuty configuration posture
  (detector enablement, trusted IP list coverage, feature coverage).
- `/aws:audit-securityhub-control` for Security Hub finding compliance
  on the same account.
- `/aws:audit-cloudtrail-org-trail` when the CloudTrail trail has gaps
  that block IAM finding investigation.
