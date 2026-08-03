---
name: iam-least-privilege-advisor
description: >-
  Analyzes AWS IAM policies to identify over-permissive grants and provides
  least-privilege remediation guidance. Use when reviewing IAM policies,
  checking for wildcard permissions, auditing role or user privileges, or
  tightening access control scope.
version: 0.1.0
---

# IAM Least-Privilege Advisor

An AWS CloudOps agent skill that analyzes IAM policy documents to identify
over-permissive grants, classify each policy against least-privilege
principles, and provide specific remediation guidance.

## Classification logic (apply in order)

1. If a statement has `Effect: Allow` with `Action: "*"` AND `Resource: "*"`,
   the policy is **OVERPERMISSIVE** (admin wildcard — maximum blast radius;
   grants every action on every resource in the account).

2. If a statement has `Effect: Allow` with any wildcard action
   (e.g., `s3:*`, `ec2:*`, `s3:Get*`, `iam:List*`) AND `Resource: "*"`,
   the policy is **OVERPERMISSIVE** (wildcard actions on all resources —
   no scope restriction on either the action or the resource).

3. If a statement has `Effect: Allow` with wildcard actions (e.g.,
   `s3:Get*`, `s3:List*`) but scoped to specific resources (concrete ARNs),
   the policy is **AMBIGUOUS** (wildcard actions on narrow resources —
   acceptable for read-only patterns but should be reviewed).

4. If all statements have `Effect: Allow` with specific named actions (no
   wildcards) AND specific resource ARNs (no `"*"` resources), the policy is
   **LEAST_PRIVILEGE** (tightly scoped — grants the minimum needed).

5. **Aggregation:** when a policy contains multiple statements, the
   policy-level verdict is the worst verdict across all statements, where
   OVERPERMISSIVE is worse than AMBIGUOUS and AMBIGUOUS is worse than
   LEAST_PRIVILEGE.

## Output format (per policy)

```text
POLICY: <name>
VERDICT: OVERPERMISSIVE | LEAST_PRIVILEGE | AMBIGUOUS
REASON: <1-2 sentences citing the specific config>
REMEDIATION: <specific action, or "None required" if least-privilege>
```

## NEVER

- NEVER classify `Action: "*", Resource: "*"` as anything other than
  OVERPERMISSIVE. This is the most dangerous policy pattern in AWS — it
  grants administrative access to every service and resource.

- NEVER classify a service wildcard on `Resource: "*"` (e.g., `s3:*` on
  `"*"`) as LEAST_PRIVILEGE. The resource wildcard means every bucket, every
  object, every setting — the action wildcard adds deletion and config
  changes on top.

- NEVER assume a policy is safe because the role name sounds harmless
  (e.g., "ReadOnlyRole"). Verify the policy document itself.

- NEVER recommend managed policies (e.g., `AdministratorAccess`,
  `PowerUserAccess`) as remediation — they reintroduce the blast radius you
  are trying to constrain.

## Remediation guidance

For **OVERPERMISSIVE** policies:

- Replace wildcard actions with the specific named actions the workload
  requires (derive from CloudTrail `EventSource` + `EventName`).
- Replace `Resource: "*"` with the specific ARN(s) the workload accesses.
- For admin wildcards: create a scoped inline policy or use
  `aws iam simulate-principal-policy` to discover actual usage.
- Consider AWS Access Analyzer to generate a least-privilege policy from
  CloudTrail activity.

For **AMBIGUOUS** policies:

- Review whether the wildcard action pattern could grant unintended
  permissions (e.g., `s3:Get*` includes `s3GetObjectTorrent`).
- Tighten to explicit named actions where feasible.

For **LEAST_PRIVILEGE** policies:

- No remediation required. Confirm the policy is attached only to the
  intended principal.

## Domain

AWS CloudOps / IAM Security & Compliance.
