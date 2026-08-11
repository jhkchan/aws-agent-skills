---
description: Provision SSM Patch Baselines with secure patch-management defaults — approval rules, compliance severity, patch groups, maintenance window integration, and custom repositories for Amazon Linux 2023, Windows, macOS, Ubuntu, and RHEL. Emits a READY_TO_DEPLOY checklist with verification commands and blocks product-OS mismatches and missing instance roles.
nl_triggers:
  - "create patch baseline"
  - "provision ssm patch baseline"
  - "deploy patch baseline"
  - "approval rule patching"
  - "auto-approve patches"
  - "patch group"
  - "register patch baseline"
  - "maintenance window patching"
  - "amazon linux 2023 patches"
  - "macos patching ssm"
  - "windows server patch baseline"
  - "ubuntu patch baseline"
  - "rhel patch baseline"
  - "custom repository patching"
  - "patch compliance severity"
  - "ssm create-patch-baseline"
  - "register-patch-baseline-for-patch-group"
  - "default patch baseline"
  - "aws-runpatchbaseline"
routes_to: ssm-patch-baseline-deployer
---

# /aws:deploy-ssm-patch-baseline

Activate the `ssm-patch-baseline-deployer` skill and provision SSM Patch
Baselines with secure patch-management defaults.

## What it does

The skill walks a pre-check gate and emits a READY_TO_DEPLOY checklist:

1. Baseline name uniqueness (no collision with existing custom baselines)
2. Operating system support (AMAZON_LINUX_2023, WINDOWS_SERVER, MACOS, etc.)
3. Product-OS matching (product filter must match the OS exactly)
4. Classification validity (Security, Bugfix, Critical Updates, etc.)
5. Severity validity (Critical, Important, Medium, Low, MSRC_SEVERITY)
6. ApproveAfterDays range (0-100, where 0 = immediate)
7. ComplianceLevel non-UNSPECIFIED for production baselines
8. Patch Group tag key exact match ("Patch Group", case-sensitive)
9. Instance role includes AmazonSSMManagedInstanceCore
10. RejectedPatchesAction (BLOCK_AS_PENDING or ALLOW_AS_DEPENDENCY)
11. Maintenance window existence and task document (AWS-RunPatchBaseline)
12. MaxConcurrency and MaxErrors explicitly set for production tasks
13. IAM permissions (ssm:CreatePatchBaseline, etc.)

## When to use

- You need to create a patch baseline for any supported OS.
- You are configuring auto-approval rules (classification, severity, delay).
- You want to register a patch group for tag-based targeting.
- You need to integrate a baseline with a maintenance window.
- You want to set up custom repositories for air-gapped patching.
- You are configuring macOS, Amazon Linux 2023, or Windows patching.

## How to invoke

### Slash command

```
/aws:deploy-ssm-patch-baseline
```

Then provide: baseline name, region, operating system, approval rules
(product, classification, severity, ApproveAfterDays, ComplianceLevel),
patch group, and optional maintenance window ID.

### Natural language

Any of these routes to the same skill:

- "create a patch baseline for Amazon Linux 2023"
- "set up Windows Server critical patch auto-approve"
- "configure macOS patching via SSM"
- "register a patch group for my web fleet"
- "integrate patch baseline with maintenance window"

### CLI routing

```bash
node cli/bin/cli.js route "create an ssm patch baseline"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or update
patch baselines, register patch groups, or integrate with maintenance
windows. The output checklist feeds into verification pipelines.

## Example

```
You: /aws:deploy-ssm-patch-baseline

     Create a production patch baseline for Amazon Linux 2023 in
     us-east-1. Auto-approve Security and Bugfix patches (Critical/
     Important) after 7 days. Patch group: al2023-prod-web.
     Account: 111111111111.

Skill:
  BASELINE: al2023-prod-security
  VERDICT: READY_TO_DEPLOY
  TARGET: al2023-prod-security
  PRE_CHECKS:
    [PASS] Baseline name unique
    [PASS] Product Amazon Linux 2023 matches OS
    [PASS] Classifications valid for AL2023
    [PASS] ApproveAfterDays 7 (range 0-100)
    [PASS] ComplianceLevel CRITICAL
    [PASS] Instance role includes AmazonSSMManagedInstanceCore
  OPERATING_SYSTEM: AMAZON_LINUX_2023
  APPROVAL_RULES: 1 rule (Security, Bugfix; auto-approve: 7 days)
  COMPLIANCE_LEVEL: CRITICAL
  PATCH_GROUPS: 1 (al2023-prod-web)
```

## References

- Skill definition: `skills/ssm-patch-baseline-deployer/SKILL.md`
- Baseline config & approval rules: `skills/ssm-patch-baseline-deployer/references/baseline-config-and-approval-rules.md`
- Patch groups & maintenance windows: `skills/ssm-patch-baseline-deployer/references/patch-groups-and-maintenance-windows.md`
- Eval suite: `skills/ssm-patch-baseline-deployer/evals/evals.json`
