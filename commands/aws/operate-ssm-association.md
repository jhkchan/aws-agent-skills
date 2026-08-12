---
description: Operates an AWS Systems Manager (SSM) State Manager association with production defaults (document/target/schedule model, tag-vs-instanceID targeting, integer rate control, KMS-encrypted S3 output, compliance reporting, versioning, remediation). Emits an OPERATION_COMPLETED checklist with verification commands.
nl_triggers:
  - "create ssm association"
  - "ssm state manager"
  - "ssm association schedule"
  - "ssm association rate control"
  - "ssm association targets"
  - "ssm association output s3"
  - "ssm association compliance"
  - "ssm association version"
  - "ssm document parameters"
  - "ssm association remediation"
  - "apply patch baseline"
  - "gather software inventory"
  - "ssm document lifecycle"
  - "max-concurrency"
  - "max-errors"
  - "state manager"
routes_to: ssm-association-operator
---

# /aws:operate-ssm-association

Activate the `ssm-association-operator` skill and operate an AWS
Systems Manager State Manager association with production-grade
defaults.

## What it does

The skill walks the operating procedure and emits an
OPERATION_COMPLETED checklist:

1. Document/target/schedule model (AWS-managed or custom document)
2. Targets: tag (dynamic) vs instance IDs (static) vs resource groups
3. Rate control: integer counts for max-concurrency and max-errors
   (NOT percentage strings)
4. Schedule: AWS cron (6 fields, seconds-first) or rate expressions
5. Output location: S3 bucket with KMS-encrypted SSE (customer-managed
   key)
6. Apply-at-creation: enabled for immediate first-run validation
7. Association status and compliance reporting
8. Association versioning (update, default version, rollback)
9. Remediation on non-compliance (EventBridge → StartAssociationsOnce)
10. Multi-document associations (separate associations or step-docs)
11. SSM document lifecycle (create/update/default version)
12. CloudWatch metrics for association execution observability

## When to use

- You need to create an SSM State Manager association.
- You are scheduling patch baseline application, inventory collection,
  or custom configuration runs.
- You are targeting instances by tag (dynamic) or instance ID (static).
- You need to configure rate control (max-concurrency, max-errors).
- You are routing association execution output to an S3 bucket.
- You are wiring remediation for non-compliant drift.
- You are versioning an association or its underlying document.
- You need compliance reporting for audit.

## When NOT to use

- **Ad-hoc one-off command runs (RunCommand)** — use ssm-run-command
  skills. State Manager is for scheduled, recurring configuration
  enforcement.
- **Patch baseline creation** — use `ssm-patch-baseline-deployer` to
  create the patch baseline itself. This skill applies the baseline
  via an association.
- **Session Manager troubleshooting** — use
  `ssm-session-troubleshooter`.
- **Association failure diagnosis** — use
  `ssm-association-troubleshooter` for diagnosing existing failures.
  This skill creates and operates associations; it does not diagnose.

## How to invoke

### Slash command

```
/aws:operate-ssm-association
```

Then provide: association name, document name (AWS-managed or
custom), target type (tag/instance ID/resource group) and values,
schedule (rate or cron), rate control (integer counts), output S3
bucket (with KMS key), parameters, tags.

### Natural language

Any of these routes to the same skill:

- "create an SSM association to patch production instances every 30
  minutes"
- "set up a state manager association for inventory collection"
- "apply a custom hardening document to my web fleet on a schedule"
- "configure rate control for my patching association"
- "wire remediation for non-compliant drift on my config association"
- "route SSM association output to a KMS-encrypted bucket"

### CLI routing

```bash
node cli/bin/cli.js route "create ssm association"
```

## Pipeline integration

This skill operates in **Phase 2 (Operate)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or operate
SSM State Manager associations. The output checklist feeds into
verification pipelines and downstream compliance-audit skills.

## Example

```
You: /aws:operate-ssm-association

     Create an SSM association named PatchProductionFleet that
     patches instances tagged Environment=production every 30
     minutes. Allow 10 in parallel, stop after 3 errors. Send
     output to my-ssm-output with KMS encryption. Run on creation.

Skill:
  SSM_ASSOCIATION: PatchProductionFleet (a-1a2b3c4d5e6f7g8h9)
  VERDICT: OPERATION_COMPLETED
  CHECKLIST:
    [✓] Document: AWS-ApplyPatchBaseline (default version)
    [✓] Targets: tag:Environment=production (dynamic)
    [✓] Schedule: rate(30 minutes)
    [✓] Apply-at-creation: ENABLED
    [✓] Rate control: max-concurrency=10, max-errors=3 (integer form)
    [✓] Output S3: s3://my-ssm-output/ssm-output/ (SSE-KMS)
  VERIFICATION_COMMANDS:
    aws ssm describe-association --association-id a-1a2b3c4d5e6f7g8h9 --region us-east-1
    aws ssm describe-association-executions --association-id a-1a2b3c4d5e6f7g8h9 --region us-east-1
```

## References

- Skill definition: `skills/ssm-association-operator/SKILL.md`
- Rate control and targeting guide: `skills/ssm-association-operator/references/rate-control-and-targets.md`
- Output and compliance guide: `skills/ssm-association-operator/references/output-and-compliance.md`
- Eval suite: `skills/ssm-association-operator/evals/evals.json`
