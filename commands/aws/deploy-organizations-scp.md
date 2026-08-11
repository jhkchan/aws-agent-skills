---
description: Provision AWS Organizations SCPs with strategy patterns (guardrail / throttle / delegate), intersection-aware blast-radius analysis, aws:CalledVia support, and a CONFIRM gate with documented rollback path.
nl_triggers:
  - "create an SCP"
  - "Service Control Policy"
  - "deny region SCP"
  - "block AWS regions"
  - "deny services SCP"
  - "require encryption SCP"
  - "deny root access SCP"
  - "SCP guardrail"
  - "OU inheritance"
  - "attach SCP to OU"
  - "attach SCP to account"
  - "delegate within SCP"
  - "aws:CalledVia"
  - "Control Tower guardrail"
  - "CloudFormation StackSets SCP"
  - "enable policy type"
  - "landing zone preventive controls"
  - "organizations policy"
routes_to: organizations-scp-deployer
---

# /aws:deploy-organizations-scp

Activate the `organizations-scp-deployer` skill and produce a
deployment plan for an AWS Organizations Service Control Policy with
safe defaults.

## What it does

Reads an SCP deployment specification (strategy, target, policy goal,
condition keys) and produces an ordered deployment plan with:

1. Pre-flight specification gate — validates org feature set,
   policy-type enabled on root, target (root/OU/account) exists,
   caller IAM permissions, and the strategy-vs-FullAWSAccess
   interaction. Blocks deployment (PREREQUISITES_MISSING) when policy
   type is not enabled or when a delegate strategy is requested
   without a tested allowlist.
2. Strategy classification — guardrail (default, additive Deny with
   FullAWSAccess preserved), throttle (Deny with condition keys
   like `aws:RequestedRegion` or `ec2:InstanceType`), or delegate
   (Allow allowlist after FullAWSAccess removal — HIGH RISK with
   explicit lockout warning).
3. SCP authoring — statement shape (Effect, Action, Resource,
   optional Condition). Principal element is omitted (silently
   ignored by SCPs). Condition keys used: `aws:RequestedRegion`,
   `aws:PrincipalType`, `aws:PrincipalArn`, `aws:CalledVia`,
   `aws:CalledViaFirst`, `aws:CalledViaLast`, `aws:RequestTag/<key>`.
4. Intersection-aware blast-radius analysis — every parent OU's SCP
   set is intersected with the new policy before attach. Root Deny
   statements cannot be overridden at child OUs; flag this and
   recommend OU-scoped Deny or condition keys instead.
5. aws:CalledVia for chained services — scope which chained services
   may act on the principal's behalf (e.g., CloudFormation-driven
   IAM role creation, Service Catalog launches).
6. Common guardrail library — drop-in templates for deny-regions,
   deny-services, deny-root-user, deny-leave-org, require-encryption,
   cap-instance-types, allowlist-approved-services.
7. CloudFormation StackSets deployment path — IaC alternative via
   `AWS::Organizations::Policy` with `DeploymentTargets` specifying
   OU IDs; StackSets auto-reconciles as accounts join the OU.
8. CONFIRM gate with rollback path — every state-changing command is
   gated; rollback path (detach-policy) is documented inline;
   management-account break-glass is named explicitly.

Emits a deterministic deployment plan per policy:

```text
POLICY_SPEC: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
ARCHITECTURE:
  Strategy / Target / Scope / FullAWSAccess / Statements / Condition keys
CHECKLIST:
  [x] Policy type SERVICE_CONTROL_POLICY enabled on root
  [x] Strategy pattern documented
  [x] Intersection with parent SCPs evaluated
  [x] FullAWSAccess preserved (guardrail) OR explicitly removed (delegate)
  [x] Principal element omitted
  [x] Condition keys valid
  [x] Rollback path documented
  [x] Dry-run validation passed
FINDINGS:
  - [INFO] Blast radius (N accounts, M OUs)
  - [WARN] Lockout warning for delegate strategy
DEPLOY_COMMANDS:
  <ordered list of aws organizations create-policy / attach-policy commands>
```

## When to invoke

Provide an SCP deployment spec and ask any of:

- "create an SCP to deny unapproved regions"
- "build a guardrail to block root user actions"
- "use a delegate strategy to allowlist approved services"
- "scope IAM via aws:CalledVia for CloudFormation"
- "cap EC2 instance types in the sandbox OU"
- "require SSE-KMS on all S3 PutObject calls org-wide"
- "deploy SCPs via CloudFormation StackSets"
- "enable policy type on my organization root"

A bare policy goal + target + "deploy SCP" also routes here via the
orchestrator.

## Inputs

- **Required:** strategy (guardrail | throttle | delegate), target
  (root ID, OU ID, or account ID), policy_goal (deny_regions |
  deny_services | require_encryption | deny_root | delegate_allowlist
  | custom).
- **Optional:** condition_keys (aws:RequestedRegion, aws:CalledVia,
  etc.), statement_overrides, deploy_via (direct_cli |
  cloudformation_stacksets), control_tower_integration (bool).

## Outputs

- One VERDICT block per policy (READY_TO_DEPLOY or
  PREREQUISITES_MISSING).
- ARCHITECTURE summary with strategy / target / scope / condition keys.
- CHECKLIST with all 8 deployment dimensions validated.
- FINDINGS with blast-radius estimate and lockout warning (for
  delegate strategy).
- DEPLOY_COMMANDS with ordered `aws organizations create-policy` /
  `attach-policy` commands, gated by CONFIRM.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 1 Deploy specialist for Organizations Governance).
- `/aws:audit-organizations-scp` for the audit/classification side —
  the auditor finds over-broad SCPs and intersection gaps; this
  deployer provisions them.
- `/aws:deploy-iam-role` for IAM identity policies (which operate
  within the SCP boundary).
- `/aws:deploy-config-rule` for detective controls (Config rules
  complement SCP preventive controls).
