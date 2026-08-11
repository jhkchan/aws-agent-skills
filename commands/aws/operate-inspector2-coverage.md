---
description: Operate Amazon Inspector v2 coverage — enable/disable per account and region, manage EC2/ECR/Lambda coverage, configure delegated admin for Organizations, surface coverage gaps, export SBOMs, with pre-checks, CONFIRM gate, and post-verification.
nl_triggers:
  - "enable Inspector"
  - "disable Inspector"
  - "Inspector v2 coverage"
  - "EC2 scanning coverage"
  - "ECR scanning coverage"
  - "Lambda scanning coverage"
  - "Lambda code vulnerability"
  - "Inspector delegated admin"
  - "Inspector member accounts"
  - "Inspector organization scan"
  - "Inspector coverage gap"
  - "SSM agent missing Inspector"
  - "deep inspection EC2"
  - "EC2 deep inspection"
  - "SBOM export"
  - "software bill of materials"
  - "Inspector enable region"
  - "batch update EC2 deep inspection"
routes_to: inspector2-coverage-operator
---

# /aws:operate-inspector2-coverage

Activate the `inspector2-coverage-operator` skill and plan/execute
an Amazon Inspector v2 coverage operation with deterministic
pre-checks, CONFIRM gate, and post-verification.

## What it does

Reads a coverage operation spec plus the intended operation and
applies the priority-ordered pre-check sequence:

1. Pre-flight delegated admin + member + region activation gate —
   short-circuit cases where the account is in org-mode but the
   caller is a member, the region is unsupported, or the SSM agent
   is offline.
2. Pre-check gate — BLOCKED if any check fails (caller not the
   delegated admin, region not opt-in, SSM association missing,
   Lambda runtime unsupported, S3/KMS policy missing for SBOM).
3. READY — emit the exact CLI sequence with all flags populated,
   the expected duration (15-30 min EC2, 1-5 min ECR, 5-30 min
   Lambda), the expected side-effects (member ENABLED, deep
   inspection scanning begins, SBOM export to S3), and the CONFIRM
   gate prompt.
4. Execute behind CONFIRM gate — snapshot
   `batch-get-account-status` first, execute the CLI, wait for
   coverage to appear in `list-coverage`.
5. Post-verification — account status ENABLED, member ACTIVE, deep
   inspection ACTIVE, SBOM export COMPLETED. COMPLETED only if ALL
   post-verification checks pass.

Emits a deterministic VERDICT per operation:

```text
OPERATION: <enable | disable | enable-delegated-admin | update-org-config | associate-member | update-ec2-deep-inspection | enable-lambda-code-scan | configure-ecr-rescan | export-sbom | diagnose-coverage>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <account-id / region / instance-id / repository / function / sbom-report-id>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
STATE: <Inspector enable state per resource type, member relationship status, deep inspection state, SBOM export status>
NOTES: <org-mode vs standalone rationale, scan-type caveats, SSM/S3/KMS prerequisites, cost impact>
```

## When to invoke

Paste a coverage operation spec and ask any of:

- "enable Inspector for these accounts"
- "designate this account as delegated admin"
- "turn on Lambda code vulnerability scanning"
- "enable EC2 deep inspection on member account X"
- "enable rescan-on-push on ECR repository Y"
- "export an SBOM for the ECR images in account Z"
- "diagnose why these EC2 instances show 0% coverage"

A bare account ID + any operation verb ("enable Inspector",
"configure deep inspection") also routes here via the orchestrator.

## Inputs

- **Required (varies by operation):**
  - **enable:** account-id(s), region, resource types (EC2 / ECR /
    LAMBDA).
  - **enable-delegated-admin:** target delegated admin account-id.
  - **update-org-config:** autoEnable map {ec2, ecr, lambda},
    optional ec2-deep-inspection-configuration.
  - **associate-member:** target member account-id.
  - **update-ec2-deep-inspection:** instance-ids, scan-state.
  - **configure-ecr-rescan:** repository name, scanOnPush true/false.
  - **export-sbom:** report format, S3 destination, KMS key,
    resource filter criteria.
  - **diagnose-coverage:** target region/account/resource type.

## Outputs

- One VERDICT block per operation (READY, BLOCKED, or COMPLETED).
- PRE_CHECKS list with `[PASS]` / `[FAIL]` per check and reason for
  failure.
- For READY: the exact CLI sequence, expected duration, expected
  side-effects, and the CONFIRM gate prompt.
- For COMPLETED: POST_VERIFY list with `[PASS]` per check, the
  resulting enable state per resource type, the member relationship
  status, the deep inspection state, and any follow-up coverage
  audit recommendations.
- For BLOCKED: the specific failure reason and the remediation step
  (e.g., use delegated admin for org-mode members, install SSM
  agent, add layer permission, fix S3/KMS policy).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill
  is the Phase 4 Operate specialist for Inspector v2 coverage).
- `/aws:audit-inspector2-coverage` for the audit/classification
  side — the auditor finds coverage gaps and disabled resource
  types; this operator enables, configures, and remediates them.
- `/aws:operate-backup-vault` for backup operations (separate
  domain).
