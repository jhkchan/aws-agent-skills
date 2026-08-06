---
description: Audit an Amazon Verified Permissions policy store for Cedar policy validation, schema-to-policy consistency, principal/resource authorization scope, policy template usage, and validation-mode configuration gaps.
nl_triggers:
  - "audit this Cedar policy"
  - "check Verified Permissions policy store"
  - "is my Cedar policy overpermissive"
  - "bare permit Cedar"
  - "schema mismatch Cedar"
  - "policy template audit"
  - "validation mode off AVP"
  - "Cedar forbid clause"
  - "AVP authorization scope"
  - "IsAuthorized policy review"
  - "Cedar policy validation"
  - "Verified Permissions audit"
  - "policy store audit"
  - "Cedar permit too broad"
routes_to: verified-permissions-policy-auditor
---

# /aws:audit-verified-permissions-policy

Activate the `verified-permissions-policy-auditor` skill and audit one or more
Amazon Verified Permissions policy store configurations (Cedar policies +
schema + validation settings) for security exposure.

## What it does

Reads a Cedar policy document, optionally paired with the policy-store schema
and validation settings, and applies the ordered classification logic:

1. Policy validity gate — syntax and type errors produce INVALID_POLICY.
2. Schema-to-policy consistency — undeclared actions, entity types, or
   attributes produce SCHEMA_MISMATCH.
3. Authorization scope — bare permits, unscoped action/resource, weak
   conditions, and missing forbid clauses produce OVERPERMISSIVE.
4. Store configuration — validation OFF, no schema, no identity source
   produce CONFIG_GAP.
5. Aggregation — worst finding wins (INVALID_POLICY > SCHEMA_MISMATCH >
   OVERPERMISSIVE > CONFIG_GAP > OK).

Emits a deterministic VERDICT per policy:

```text
POLICY: <policy-id>
VERDICT: INVALID_POLICY | SCHEMA_MISMATCH | OVERPERMISSIVE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and rule number>
FINDINGS:
  - [OVERPERMISSIVE] <finding description (Rule Na)>
  - [CONFIG_GAP] <finding description (Config Na)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a Cedar policy and schema and ask any of:

- "audit this Cedar policy"
- "is my permit too broad?"
- "check for schema mismatches"
- "is validation mode on?"
- "review this policy template"
- "is this policy store secure?"

A policy-store ID + any audit verb ("audit this store", "check policy
store") also routes here via the orchestrator.

## Inputs

- A Cedar policy document (permit/forbid text), pasted inline or referenced
  by file path.
- Schema (JSON): entity types, actions, attributes, hierarchy. Required for
  schema-consistency checks (Step 1).
- Validation settings: `mode: STRICT | OFF`. Drives the CONFIG_GAP check.
- For template-linked policies: the parent template ID. The linked policy
  inherits all template conditions; audit the template for scope.

## Outputs

- One VERDICT block per policy (multiple findings aggregate to the worst
  verdict).
- Enumerated FINDINGS list with per-finding rule citation.
- Specific remediation: scope bare permits, add type annotations, enable
  validation, add forbid clauses, update schema.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for AVP/Cedar authorization security).
- `/aws:audit-iam-least-privilege` for IAM policy analysis of roles that may
  interact with AVP (e.g., roles with `verifiedpermissions:IsAuthorized`).
