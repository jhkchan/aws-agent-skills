# Advanced Patterns — Security Hub Finding Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Mindset

A Security Hub finding is a **control evaluation result**, not a threat.
Where GuardDuty signals an active attack, Security Hub signals a config
drift — the resource is non-compliant with a standard. Senior Security
Hub engineers read the finding's `Compliance.Status` and
`Compliance.StatusReasons` before probing the resource: a finding marked
`PASSED` that the operator is debugging is likely a stale cache; a
finding marked `FAILED` with `StatusReasons` describing a Config rule
error is an AWS-side gap, not a resource failure.

### Step 0: Non-obvious behaviours that change the diagnosis

- **A `RESOLVED` finding that keeps reappearing is a re-evaluation
  race.** Security Hub re-evaluates on Config change or periodic
  schedule. If the resource is fixed but the rule re-runs before the
  cached state propagates, the finding flips back to FAILED. Wait one
  full eval cycle (5-30 min) before escalating. If still flapping
  after 30 min, the rule is mis-attributing the resource.

- **`NOT_AVAILABLE` does NOT mean the resource is compliant.** It
  means the Config rule could not evaluate — typically because the
  resource is out of scope (Lambda control, no Lambda in account), the
  rule errored, or the source bucket is unavailable. Read
  `Compliance.StatusReasons` for the specific code.

- **Security Hub severity ≠ Config rule severity.** Security Hub
  assigns `Severity.Label` based on the standard's scoring. A CIS Low
  (severity 1.x) maps to Security Hub `INFORMATIONAL`; an FSBP
  Critical can map to either `CRITICAL` or `HIGH`.

- **Cross-account aggregation has up to 5 min latency.** A finding
  fixed in a member account may still appear FAILED in the aggregator
  for up to 5 minutes. Verify by querying the member account directly.

- **Custom controls (custom ASFF) fire from Config or EventBridge.**
  A custom Security Hub control is a Config rule (custom Lambda-backed)
  that emits ASFF via `BatchImportFindings`. If the rule exists but
  findings stop, the Lambda's `securityhub:BatchImportFindings` IAM
  permission is the usual culprit.

- **FSBP control IDs (e.g., `S3.1`, `EC2.8`) are stable; standard
  control IDs (e.g., `CIS.1.5`) change with version.** CIS 1.2 →
  CIS 1.4 added new controls; the numeric suffix may not match the
  prior runbook. Cross-reference `GeneratorId` against the current
  standard's ARN before remediating.

- **Disabling a standard mid-audit does NOT clear existing findings.**
  Findings already in the system stay ACTIVE until the next eval cycle
  (or 3-5 days). Explicitly suppress or update the workflow status to
  clear immediately.

### Step 14: Custom actions via EventBridge → Lambda

For auto-remediation, recommend an EventBridge rule that triggers
Lambda on finding import:

```text
EventBridge source: aws.securityhub
Event pattern: { "source": ["aws.securityhub"],
  "detail-type": ["Security Hub Findings - Imported"],
  "detail": { "findings": { "Severity": { "Label": ["CRITICAL","HIGH"] },
    "Compliance": { "Status": ["FAILED"] } } } }
Target Lambda:
  - S3 public access: aws s3control put-public-access-block
  - IAM access key: aws iam update-access-key (deactivate)
  - EC2 IMDSv2: aws ec2 modify-instance-metadata-options --http-tokens required
  - KMS rotation: aws kms enable-key-rotation
Always: post to SOC chat, NEVER auto-delete a resource.
```

## Expert heuristic

When triaging a Security Hub finding, ask three questions in order.
(1) Does the finding's `Compliance.Status` match the resource's actual
state? A `FAILED` finding with no corroborating service CLI failure is
a stale cache or Config rule error — check `StatusReasons`. (2) Is the
resource in the same account and region as the finding? Cross-account
aggregation has up to 5 min latency; the member account's local view is
more current than the aggregator's. (3) Is the rule backing the control
running correctly? Config rule Lambda errors, missing IAM permissions,
and out-of-scope resource types produce `NOT_AVAILABLE` findings that
look like control failures but are evaluation gaps. A finding matching
all three (true FAILED, same region, healthy rule) is almost certainly
a real control failure — proceed to remediation.

## Recent AWS features (2024-2026)

- **Security Hub Automation Rules (2024-2025):** GA feature that lets
  customers define serverless rules to update finding fields
  automatically — severity, workflow status, notes, related findings.
  Supersedes manual `update-findings` for FP suppression. Rules are
  ordered; first match wins. Verify with `list-automation-rules` and
  `get-automation-rules`.

- **Security Hub Custom Controls (2024-2025):** Customers author
  controls in ASFF, emit findings via Config rule Lambda +
  `BatchImportFindings`. Useful for organization-specific policies
  (tag compliance, internal naming).

- **Security Hub central configuration (2024-2025):** In Organizations
  with delegated admin, the admin can push a configuration policy to
  member accounts mandating standards, custom controls, and
  Automation Rules.

- **FSBP expansion (2024-2025):** New FSBP controls for Amazon
  Bedrock (model access, guardrails), Amazon Q (data residency), and
  SageMaker (model monitoring). Control IDs are stable; check
  `describe-standards` for the latest count.

- **Security Hub cross-Region aggregation GA (2024):** A single
  aggregator account collects findings from all member accounts and
  regions. Latency up to 5 min — verify with `get-finding-aggregator`
  and `list-members`.

- **AWS Resilience Hub integration (2024):** Security Hub can receive
  findings from AWS Resilience Hub (RTO/RPO policy violations) via
  ASFF. Treat as a separate `ProductFields.ProviderName` for filtering.

- **Security Hub Inspector V2 finding deduplication (2024-2025):**
  Inspector findings now deduplicate on the same `GeneratorId` +
  resource — earlier versions produced duplicates on re-scan.

