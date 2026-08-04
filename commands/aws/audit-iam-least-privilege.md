---
description: Audit an IAM policy document for over-permissive grants, wildcard actions/resources, privilege-escalation actions (PassRole, AssumeRole), and inverse wildcards (NotAction/NotResource).
nl_triggers:
  - "is this IAM policy over-permissive"
  - "check for wildcard permissions"
  - "privilege escalation risk"
  - "least privilege check"
  - "audit this IAM role"
  - "tighten this role policy"
  - "PassRole on wildcard"
  - "AssumeRole scope"
  - "NotAction NotResource"
  - "condition key bypass"
  - "iam policy remediation"
  - "scope down this policy"
routes_to: iam-least-privilege-advisor
---

# /aws:audit-iam-least-privilege

Activate the `iam-least-privilege-advisor` skill and classify one or more IAM
policy documents against least-privilege principles.

## What it does

Reads an IAM policy document (inline or managed, pasted inline or read from
file) and applies the 10-step classification logic in declaration order:

1. Validate input and policy version (`2012-10-17` vs legacy `2008-10-17`).
2. Separate Deny from Allow (Deny narrows; never grants).
3. Admin wildcard (`Action: "*"` + `Resource: "*"`) -> OVERPERMISSIVE / CRITICAL.
4. Service / read-level wildcards on `Resource: "*"` -> OVERPERMISSIVE / HIGH.
5. Inverse wildcards (`NotAction` / `NotResource`) -> OVERPERMISSIVE.
6. Privilege-escalation actions on `"*"` (PassRole, AssumeRole, CreatePolicy,
   AttachRolePolicy, UpdateAssumeRolePolicy) -> OVERPERMISSIVE / CRITICAL.
7. Wildcard actions scoped to specific resources -> AMBIGUOUS.
8. Condition-key bypass paths (ForAllValues, SourceIp 0.0.0.0/0, Null false).
9. Resource ARN scope (partition wildcards, global bucket scope).
10. Named actions on specific ARNs -> LEAST_PRIVILEGE.

Emits a deterministic VERDICT per policy:

```text
POLICY: <name>
VERDICT: OVERPERMISSIVE | LEAST_PRIVILEGE | AMBIGUOUS
REASON: <1-2 sentences citing the specific statement and config>
RISK: CRITICAL | HIGH | MODERATE | LOW
REMEDIATION: <specific action, or "None required" if least-privilege>
```

## When to invoke

Paste a policy document and ask any of:

- "is this over-permissive?"
- "check for wildcard / escalation risk"
- "tighten this role before production"
- "what's the blast radius of this policy?"

A bare role name + any audit verb ("audit this role", "check this policy") also
routes here via the orchestrator.

## Inputs

- An IAM policy document (JSON), pasted inline or referenced by file path.
- Optional: the principal ARN and attached managed-policy names, for
  effective-permissions context (Step: Effective permissions context).

## Outputs

- One VERDICT block per policy (multi-statement policies aggregate to the worst
  statement).
- Specific remediation: scoped-down action lists, concrete resource ARNs, and
  the CloudTrail-derived least-privilege workflow for deriving replacements from
  observed API usage.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the Phase 2
  Audit specialist for IAM).
- `references/policy-analysis-guide.md` for the wildcard-pattern reference
  table and common over-permissive patterns found in the wild.
