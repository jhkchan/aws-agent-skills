# Advanced Patterns — Security Hub Remediation Automator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Step 0: Expert knowledge — non-obvious Security Hub behaviors

- **Finding events use `detail-type: "Security Hub Findings - Imported"`.**
  NOT "Custom Action". Confusing the two is the most common automation
  failure.

- **`batch-update-findings` requires BOTH `Id` and `ProductArn`.** Missing
  either produces `InvalidInput`.

- **Security Hub deduplicates findings by generator ID + resource.** The
  finding ID stays constant across re-evaluations. Key idempotency on
  finding `Id`, not `UpdatedAt`.

- **Control standards take 5-30 minutes to fully enable.** Wait for
  `STANDARD_REGISTRATION_COMPLETE` before wiring EventBridge rules.

- **Suppressed findings can be un-suppressed by re-evaluation.** If the
  control regenerates with a new finding ID, the old suppression does
  NOT apply. The suppression evaluator must check by generator ID.

- **The delegated administrator cannot create custom actions on behalf
  of members.** Custom actions are per-account. Use CloudFormation
  StackSets for bulk deployment.

- **EventBridge target needs an input transformer.** The finding is
  nested in `detail.findings[0]`. Without a transformer, the Lambda
  receives the full envelope and must parse manually.

- **`WorkflowStatus: RESOLVED` does NOT prevent re-opening.** If the
  control re-evaluates and the resource is still non-compliant, the
  finding re-opens with NEW. Always verify the fix before closing.


### FORBIDDEN — NEVER do these

1. NEVER wire an EventBridge rule on `aws.securityhub` without a
   `Severity.Label` filter. Without it the rule fires on EVERY finding
   including LOW and INFORMATIONAL, overwhelming Lambda concurrency and
   spiking costs.

2. NEVER use `update-findings` (deprecated). Use `batch-update-findings`
   which accepts up to 100 findings per call and is the forward-compatible
   API.

3. NEVER suppress a finding without an expiration date in the Note.
   Permanent suppression violates PCI DSS, SOC 2, ISO 27001. Always set
   "Suppressed until YYYY-MM-DD" and run a daily evaluator Lambda.

4. NEVER auto-remediate without calling `batch-update-findings` afterward.
   A remediation that fixes the resource but leaves the finding in NEW
   status triggers duplicate remediation and corrupts dashboards.

5. NEVER deploy a Lambda remediation function without an SQS DLQ on the
   EventBridge target. Failed invocations are silently dropped without a
   DLQ; the finding stays open and no one knows.

6. NEVER confuse `detail-type: "Security Hub Findings - Imported"` with
   `"Security Hub Findings - Custom Action"`. The former is for
   automation (fires on ingestion); the latter fires on human console
   click.

7. NEVER key remediation idempotency on `UpdatedAt`. Security Hub
   re-evaluates controls periodically, changing `UpdatedAt` without
   changing the finding state. Key on finding `Id`.


## Anti-Patterns — NEVER do these things

- NEVER wire an EventBridge rule on `aws.securityhub` without a
  `Severity.Label` filter. The rule fires on EVERY finding, including
  LOW, producing cost spikes and Lambda concurrency exhaustion.

- NEVER use `update-findings` (deprecated). Use `batch-update-findings`
  for all workflow status changes. The old API is single-finding and
  does not support batch updates.

- NEVER suppress a finding without an expiration date. Permanent
  suppression violates PCI DSS, SOC 2, ISO 27001. Always include
  "Suppressed until YYYY-MM-DD" and run the daily evaluator Lambda.

- NEVER auto-remediate without calling `batch-update-findings`
  afterward. A remediation that fixes the resource but leaves the
  finding in NEW status triggers duplicate remediation.

- NEVER deploy a Lambda remediation function without an SQS DLQ on
  the EventBridge target. Failed invocations are silently dropped.

- NEVER enable a compliance standard in production without staging
  validation. Standards generate findings immediately — hundreds in
  minutes in an unprepared account.

- NEVER confuse `detail-type: "Security Hub Findings - Imported"`
  with `"Security Hub Findings - Custom Action"`. The former is for
  automation; the latter fires on human console click.

- NEVER key idempotency on `UpdatedAt`. Security Hub re-evaluates
  periodically, changing `UpdatedAt` without changing state. Key on
  finding `Id` for deduplication.


## Appendix A — Common finding-to-runbook mappings

| Standard | Control | Finding type | Runbook | Strategy |
|---|---|---|---|---|
| FSBP | S3.1 | S3 public access | `AWS-DisableS3BucketPublicAccess` | Auto |
| FSBP | S3.4 | S3 missing encryption | `AWS-EnableS3BucketEncryption` | Auto |
| FSBP | IAM.3 | IAM unused key | `AWS-IAMRevokeUnusedAccessKey` | Auto (caveat) |
| FSBP | CloudTrail.1 | Trail disabled | `AWS-EnableCloudTrailLogging` | Auto |
| CIS | 4.1 | SG open to 0.0.0.0/0 | Custom Lambda | REVIEW_REQUIRED |


## Appendix B — Decision tree

```
Managed SSM runbook for the finding type?
+-- Yes -> Severity CRITICAL or HIGH?
|         +-- Yes -> AUTOMATION_DEPLOYED
|         +-- No  -> MEDIUM_NOTIFY or LOW_NOTIFY
+-- No  -> Custom Lambda feasible?
          +-- Yes -> Build + test -> AUTOMATION_DEPLOYED
          +-- No  -> REVIEW_REQUIRED (gap cited)
```


## Recent AWS features (2024-2026)

- **Security Hub centralized configuration (2024):** Delegated admin can
  push policies and control enablements across all members centrally.
- **Finding aggregation across regions (2024-2025):** Single region
  aggregates findings from all enabled regions, simplifying rule design.
- **SSM runbook native finding updates (2025):** SSM `aws:updateSecurityHubFinding`
  action eliminates the need for a separate Lambda to close findings.
- **Controls for new services (2025-2026):** FSBP controls for Amazon Q,
  Bedrock, and GenAI services. Remediation runbooks shipping incrementally.


## Expert heuristic: blast radius of auto-remediation

> ALWAYS validate the EventBridge severity filter and Lambda dispatch
> table in a non-production account first. Deploy with a dry-run flag
> in the Lambda for 48 hours: log what it WOULD do without calling SSM.
> Then enable live execution after verifying zero false positives.

**Pre-production validation protocol:**

1. Deploy EventBridge rule + Lambda in staging. Plant 5 deliberate findings.
2. Run Lambda in dry-run mode 48 hours. Verify mapping correctness.
3. Enable live execution. Verify all 5 remediated AND closed via
   `batch-update-findings`.
4. Promote to production with severity filter active.
