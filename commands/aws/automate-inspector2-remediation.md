---
description: Design Amazon Inspector v2 automated remediation workflows with severity-based response (Critical = SSM patch via AWS-RunPatchBaseline with snapshot gate, High = notify, Medium/Low = maintenance window), EventBridge routing for finding events, ECR image scan on push integration with CodeBuild rebuild trigger, Lambda code scan finding handling (CI/CD redeploy required, not SSM patch), finding suppression for accepted risks with documented rationale, Inspector to Security Hub forwarding, multi-account via Organizations delegated admin, SSM patch baseline association with severity-to-baseline mapping, finding lifecycle (OPEN / SUPPRESSED / CLOSED), and SLA enforcement via scheduled Lambda. Enforces guardrails — snapshot before patch, Operation Scan before Install, 3-cycle validation (scan non-prod, install non-prod, install prod), DLQ on every EventBridge target, CloudTrail audit on every action. Emits AUTOMATION_DEPLOYED with workflow template or REVIEW_REQUIRED with the specific gap.
nl_triggers:
  - "automate Inspector finding"
  - "Inspector v2 remediation"
  - "Inspector2 automation"
  - "ECR image scan on push"
  - "Lambda code scan finding"
  - "Inspector to Security Hub"
  - "severity-based remediation"
  - "SSM patch baseline for Inspector"
  - "Inspector delegated admin"
  - "Inspector finding suppression"
  - "container image rebuild"
  - "Inspector EventBridge"
  - "Critical finding auto-patch"
  - "AWS-RunPatchBaseline Inspector"
  - "Inspector finding lifecycle"
  - "Inspector SLA enforcement"
  - "Inspector multi-account org"
routes_to: inspector2-automation-automator
---

# /aws:automate-inspector2-remediation

Activate the `inspector2-automation-automator` skill and design an
Inspector v2 automation workflow with the right severity-based
response and verification.

## What it does

Reads an Inspector finding or finding class (EC2 OS CVE, ECR
container image CVE, Lambda code scan finding), severity context
(Critical / High / Medium / Low), and response scope (auto-patch /
notify / rebuild / suppress), then applies a 14-step design process:

1. Classify the finding source (EC2 OS / ECR image / Lambda code).
2. Enable Inspector (EC2 / ECR / Lambda) and verify coverage.
3. Map the resource type to a remediation strategy.
4. Decide severity-based response (the severity matrix).
5. Wire EventBridge rule for findings.
6. SSM patch baseline for OS findings (with severity-to-baseline mapping).
7. SSM Automation runbook for patching (with snapshot gate).
8. ECR image scan on push + scheduled rescan + rebuild trigger.
9. Lambda code scan finding handling (notify + CI/CD redeploy).
10. Inspector to Security Hub forwarding.
11. Finding suppression for accepted risks.
12. Multi-account via delegated admin.
13. Finding lifecycle and SLA enforcement.
14. Patch baseline association to instances (Patch Group tagging).

Emits a deterministic VERDICT per finding class:

```text
FINDING: <reference>
SEVERITY: <CRITICAL | HIGH | MEDIUM | LOW>
DETECTION:
  - Source: <aws.inspector2 via EventBridge>
  - Resource: <type + identifier>
  - CVE: <id + package>
RESPONSE:
  - Action: <SSM patch | CodeBuild rebuild | Lambda update | notify | suppress>
  - SLA: <days>
  - Automation: <EventBridge -> SSM | Lambda -> CodeBuild>
SSM_RUNBOOK: <AWS-RunPatchBaseline | custom document | n/a>
VERIFICATION:
  - Rescan: aws inspector2 list-findings --filter-criteria status=OPEN
  - Security Hub: aws securityhub get-findings --filter-criteria RecordState=ACTIVE
MULTI_ACCOUNT: <single | delegated-admin | REVIEW_REQUIRED>
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
GAP: <if REVIEW_REQUIRED, the specific missing piece>
TEMPLATE: <CLI snippet or YAML for the workflow>
```

## When to invoke

Paste an Inspector finding or automation requirement and ask:

- "auto-patch Critical Inspector findings on EC2"
- "trigger CodeBuild rebuild on Critical ECR finding"
- "notify Slack on High Lambda code scan finding"
- "configure Inspector multi-account via delegated admin"
- "suppress accepted-risk finding with documented rationale"
- "validate our Inspector automation workflow"
- "wire SSM patch baseline for Inspector Critical CVEs"
- "schedule weekly ECR rescan for new CVEs"
- "forward Inspector findings to Security Hub"

A bare Inspector finding ARN or finding class + any automate verb
routes here via the orchestrator.

## Inputs

- **Required:** finding_source (EC2 OS / ECR image / Lambda code /
  network reachability / secret detection), severity (Critical /
  High / Medium / Low), resource_identifier (instance ID, ECR
  repo+tag, Lambda function ARN).
- **Recommended:** response_scope (auto-patch / notify / rebuild /
  suppress), sns_topic_arn, codebuild_project_arn (for ECR
  rebuild), lambda_ci_cd_pipeline (for Lambda updates), ssm_role_arn.
- **For multi-account:** org_id, management_account_id,
  delegated_admin_account_id, member_account_list.
- **For suppression:** finding_arn, suppression_rationale (CISO
  approval, decommission schedule, isolated VPC, no patch available).
- **For patching:** patch_group_tag, pre_prod_validation_status
  (Cycle 1 Scan / Cycle 2 Install / Cycle 3 prod).

## Outputs

- One FINDING block per finding class with SEVERITY, DETECTION,
  RESPONSE, SSM_RUNBOOK, VERIFICATION, MULTI_ACCOUNT, VERDICT, and
  TEMPLATE fields.
- For AUTOMATION_DEPLOYED verdicts: a working EventBridge rule +
  SSM Automation / CodeBuild / Lambda stub with the exact parameter
  mapping and execution role trust policy.
- For REVIEW_REQUIRED verdicts: a specific GAP citation (delegated
  admin not configured, SSM agent missing on instance, patch
  baseline ApproveAfterDays too high, missing snapshot gate, etc.).
- Expert-knowledge callouts (ECR scans push-time not continuous,
  Lambda code scans static-only, SCP/IAM non-detach analog, 3-cycle
  validation protocol).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Automate specialist for Inspector-driven security).
- `/aws:audit-inspector2-coverage-findings` for Inspector coverage
  posture audits (this skill designs automation; the auditor
  reviews configuration).
- `/aws:troubleshoot-inspector2-finding` for individual finding
  investigation (this skill automates the response).
- `/aws:operate-inspector2-coverage` for enable / disable operations
  (this skill wires post-detection automation).
- `/aws:automate-securityhub-remediation` for Security Hub sourced
  findings (Inspector forwards to SecHub; this skill handles the
  Inspector source directly with lower latency).
---
