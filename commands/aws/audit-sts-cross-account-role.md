---
description: Audit an IAM role trust policy (AssumeRolePolicyDocument) for cross-account/external trust, wildcard Principal grants, confused-deputy service-principal vectors, and condition-strength weaknesses.
nl_triggers:
  - "who can assume this role"
  - "audit role trust policy"
  - "cross-account role trust"
  - "ExternalId missing"
  - "confused deputy"
  - "Principal star"
  - "Principal wildcard"
  - "service principal trust"
  - "AssumeRolePolicyDocument audit"
  - "role trust security"
  - "SourceArn missing"
  - "SourceAccount condition"
  - "SAML federated trust"
  - "NotPrincipal trust policy"
  - "role assumption exposure"
routes_to: sts-cross-account-role-auditor
---

# /aws:audit-sts-cross-account-role

Activate the `sts-cross-account-role-auditor` skill and classify one or more
IAM role trust policies (AssumeRolePolicyDocument) against cross-account and
external-trust principles.

## What it does

Reads an IAM role trust policy (pasted inline or read from file) and applies
the 9-step classification logic in declaration order:

1. Validate input and extract owning account (Step 0).
2. Inverse wildcards: `NotPrincipal` / `NotAction` -> WILDCARD_TRUST (Step 1).
3. Wildcard Principal (`"*"`, `{"AWS": "*"}`) -> WILDCARD_TRUST / CRITICAL (Step 2).
4. Cross-account root/role ARN without `sts:ExternalId` -> EXTERNAL_TRUST / HIGH (Step 3).
5. Confused-deputy service principal without `aws:SourceArn`/`aws:SourceAccount` -> EXTERNAL_TRUST / HIGH (Step 4).
6. Confused-deputy WITH source guard -> CONDITIONAL (Step 5).
7. SAML/OIDC federated trust -> evaluate conditions (Step 6).
8. Session-tag injection check (`sts:TagSession` without `sts:TransitiveTagKeys`) (Step 7).
9. Same-account scoped -> OK (Step 8).
10. Aggregate to worst statement (Step 9).

Emits a deterministic VERDICT per role:

```text
ROLE: <name>
VERDICT: EXTERNAL_TRUST | WILDCARD_TRUST | CONDITIONAL | OK
REASON: <1-2 sentences citing the specific statement, Principal type, and guard status>
RISK: CRITICAL | HIGH | MODERATE | LOW
REMEDIATION: <specific action, or "None required" if OK>
```

## When to invoke

Paste a role trust policy and ask any of:

- "who can assume this role?"
- "audit this role trust policy"
- "is this role open to cross-account access?"
- "check for confused-deputy risk"
- "does this trust policy need an ExternalId?"
- "is this service principal safe without SourceArn?"

A bare role name + any trust-audit verb ("audit this role's trust", "check
who can assume this") also routes here via the orchestrator.

## Inputs

- An IAM role trust policy document (JSON), pasted inline or referenced by
  file path. Must include `Version`, `Statement` with `Effect`, `Principal`,
  and `Action`.
- Optional: the role ARN (for same-account verification — extracts the owning
  account ID to distinguish same-account from cross-account principals).
- Optional: the role's permissions policy summary, for severity escalation
  (if the role has `iam:PassRole` or admin-level permissions, severity
  escalates by one level).

## Outputs

- One VERDICT block per role (multi-statement trust policies aggregate to the
  worst statement).
- Specific remediation: add ExternalId, add SourceArn/SourceAccount, replace
  root ARN with specific role ARN, remove wildcard Principal, add
  `sts:TransitiveTagKeys` limit.

## Related

- `/aws:audit-iam-least-privilege` to audit the role's **permissions policy**
  (what the role can do after assuming it). This skill audits the **trust
  policy** (who can assume the role). Both surfaces should be audited.
- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for STS trust policies).
- `references/trust-policy-hardening-guide.md` for the confused-deputy
  service-principal reference table and copy-pasteable remediation commands.
