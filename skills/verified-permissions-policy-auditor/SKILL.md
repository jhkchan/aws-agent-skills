---
name: verified-permissions-policy-auditor
description: Audits Amazon Verified Permissions policy stores for Cedar policy validation, schema-to-policy consistency, principal/resource authorization scope, policy template usage, and validation-mode configuration gaps. Emits a deterministic verdict (INVALID_POLICY | SCHEMA_MISMATCH | OVERPERMISSIVE | CONFIG_GAP | OK) per policy with enumerated findings and CLI remediation. Use when reviewing Cedar policies, checking for bare-permit overexposure, validating schema consistency, auditing template-linked policies, or hardening AVP policy stores before production deployment.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline policy-document classification. Live-account audits use aws verifiedpermissions get-policy-store, get-policy, get-schema, and list-policies (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  verdict_shape: INVALID_POLICY | SCHEMA_MISMATCH | OVERPERMISSIVE | CONFIG_GAP | OK
  when_to_use: Reviewing a Cedar policy before production deployment, checking for bare or over-permissive permit clauses, validating schema-to-policy consistency, auditing template-linked policies, inspecting validation-mode configuration, or hardening Amazon Verified Permissions policy-store posture.
  activation_triggers: audit this Cedar policy, check Verified Permissions policy store, is my Cedar policy overpermissive, bare permit Cedar, schema mismatch Cedar, policy template audit, validation mode off AVP, Cedar forbid clause, AVP authorization scope, IsAuthorized policy review
  invocation_schema: 'Input: either (a) a Cedar policy document (optionally paired with the policy-store schema and validation settings), OR (b) a policy-store-id for live-account audit. Output: deterministic POLICY/VERDICT/REASON/FINDINGS/ REMEDIATION block per policy, where VERDICT belongs to {INVALID_POLICY, SCHEMA_MISMATCH, OVERPERMISSIVE, CONFIG_GAP, OK, ERROR}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Verified Permissions, Cedar, policy store, authorization, permit, forbid, bare permit, schema validation, policy template, principal scope, IsAuthorized, entity hierarchy, Cedar syntax, authorization model, AVP audit, overpermissive policy, template-linked, validation mode, Cedar type checking, action scope
  tags: verified-permissions, cedar, security, authorization, policy-store, schema-validation, audit
---

# Verified Permissions Policy Auditor

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across all
dimensions, and two Cedar patterns are in a class of their own —
`permit(principal, action, resource);` with no scope constraints (bare permit,
authorizes EVERY request), and `validationSettings.mode: OFF` (silent schema
divergence — policies can reference non-existent entities without detection).

Amazon Verified Permissions (AVP) uses Cedar, a purpose-built authorization
language evaluated against a schema that declares entity types, actions, and
hierarchies. Unlike IAM JSON policies, Cedar separates **policy text** from
**schema definition**, creating a consistency surface that IAM does not have.

- A **bare permit** is the Cedar equivalent of IAM `Principal:"*",
  Action:"*", Resource:"*"` — it matches every authorization request without a
  single condition. One policy, total access.
- **`forbid` overrides `permit`** — a request is ALLOW only if at least one
  `permit` matches AND no `forbid` matches. Cedar's default decision is DENY.
- **Validation mode OFF** disables schema checking at policy-creation time —
  policies referencing undeclared actions or entity types are silently
  accepted, causing silent authorization failures or unexpected allows.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| Policy has syntax/type error (e.g., comparing Long with String) | **INVALID_POLICY** | Step 0 |
| Template slot `?principal` in a non-template (static) policy | **INVALID_POLICY** | Step 0 |
| Policy references action not in schema's `actions` | **SCHEMA_MISMATCH** | Step 1 |
| Policy references entity type not in schema's `entityTypes` | **SCHEMA_MISMATCH** | Step 1 |
| Policy accesses attribute not declared in entity's `shape` | **SCHEMA_MISMATCH** | Step 1 |
| `permit(principal, action, resource);` — no scope, no conditions | **OVERPERMISSIVE** | Step 2 |
| Unscoped `action` or `resource` with broad principal type | **OVERPERMISSIVE** | Step 2 |
| Condition trivially satisfiable + unconstrained action/resource | **OVERPERMISSIVE** | Step 2 |
| `validationSettings.mode: OFF` | **CONFIG_GAP** | Step 3 |
| No schema defined in policy store | **CONFIG_GAP** | Step 3 |
| Scoped permit + matching schema + validation ON + forbid on sensitive actions | **OK** | Step 4 |

See the ordered steps below for edge cases. Deep Cedar evaluation internals
(entity hierarchy, partial evaluation, template linking) are in the
[Deep reference](#deep-reference-cedar-authorization-internals) section.

### Quantitative risk thresholds (D1 expert calibration)

The D1 quantitative risk threshold table (condition counts, hierarchy depth, payload size, template links, quota headroom, forbid/permit ratio, namespaces) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when calibrating store-level risk.

### Cedar evaluation decision-tree heuristics (non-obvious)

Cedar evaluation heuristics (missing-entity DENY, forbid+when double-negative, absent context errors, O(p x c) cost, PutSchema full replacement) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for the undocumented evaluation semantics.

## Pre-flight: policy store metadata gate

Before evaluating individual policies, classify the store configuration.
Several store attributes **short-circuit** or constrain the audit.

**Live-account pre-flight checks (skip for offline policy-doc audit):**
Live-account pre-flight commands (UpdatePolicy permission probe, list-policies snapshot, get-schema retrieval) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before a live policy-store audit.

| Attribute | Value | Effect on audit |
|---|---|---|
| `validationSettings.mode` | `STRICT` | Policies validated against schema at creation. Schema consistency check is meaningful. |
| `validationSettings.mode` | `OFF` | No schema validation. Policies may reference non-existent entities. Jump to Step 3 (CONFIG_GAP) after Steps 0-2. |
| Schema | absent | No schema defined. Cannot check consistency. Flag as CONFIG_GAP. |
| Schema | present | Proceed with full audit (Steps 0-4). |
| Policy type | `STATIC` | Standard policy. Audit the policy text directly. |
| Policy type | `TEMPLATE` | Policy template with `?principal`/`?resource` slots. Audit the template; scope is defined by linked policies. |
| Policy type | `TEMPLATE_LINKED` | Instantiation of a template. Audit the PARENT template for conditions; the linked policy inherits all template clauses. |

**If the policy text is empty or cannot be extracted**, output:

```text
POLICY: <policy-id>
VERDICT: ERROR
REASON: Policy text is empty or could not be retrieved — cannot classify.
REMEDIATION: Retrieve the canonical policy with
`aws verifiedpermissions get-policy --policy-store-id <store> --policy-id <id>`
and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Policy validity gate (parse + type errors)

Check the Cedar policy for structural validity BEFORE schema consistency or
scope evaluation. A policy that cannot be parsed or type-checked is
unclassifiable for security purposes — it may behave differently than its text
suggests.

**Parse errors** (policy cannot be parsed at all):
- Unbalanced parentheses or braces
- Missing `;` terminator
- Invalid operators (Cedar has no `=` for equality; use `==`)
- `?principal` slot in a `STATIC` policy (slots only allowed in templates)

**Type errors** (policy parses but fails type checking):
- Comparing incompatible types (e.g., `principal.age >= "eighteen"` where `age`
  is `Long` and `"eighteen"` is `String`)
- Calling a method on the wrong type (e.g., `.contains()` on a `Long`)
- Negating a non-Boolean expression
- `principal.department` where `department` is `Set<String>` but used as scalar

If any parse or type error is found → **INVALID_POLICY**.

**Expert note — validation mode interaction:** when `validationSettings.mode`
is `OFF`, AVP does NOT type-check policies at creation time. Type errors
persist silently in the store and cause **runtime evaluation errors** during
`IsAuthorized` calls — the request returns an error instead of DENY,
potentially breaking application logic. The auditor catches these regardless
of validation mode; the validation mode only affects whether AVP would have
caught them at creation.

### Step 1: Schema-to-policy consistency

If the policy is structurally valid (Step 0 passed), verify it against the
schema. This step is only meaningful when a schema is present.

Check each element of the policy's scope clause and conditions:

- **Action references:** every `action: Namespace::Action::"name"` must exist
  in the schema's `actions` map. A policy referencing `PhotoApp::Action::"DeletePhoto"`
  when the schema only declares `ViewPhoto` and `UploadPhoto` is a mismatch.
- **Entity types:** `principal: Namespace::User` must exist in the schema's
  `entityTypes` map. Referencing `Namespace::Admin` when only `User` is
  declared is a mismatch.
- **Attribute access:** `principal.department` requires `department` to be
  declared in the entity type's `shape.attributes`. Accessing an undeclared
  attribute is both a type error (Step 0) and a schema mismatch — classify as
  SCHEMA_MISMATCH when the policy is syntactically valid Cedar but the schema
  does not declare the attribute.
- **`appliesTo` constraint:** the action's `appliesTo.principalTypes` and
  `appliesTo.resourceTypes` must include the types used in the policy's scope.
  A policy using `principal: User` for an action whose `appliesTo` only lists
  `ServiceAccount` is a mismatch even though `User` exists in the schema.

If any mismatch is found → **SCHEMA_MISMATCH**.

**Expert note — schema updates do not retroactively validate:** when the schema
is updated (e.g., an action is removed), existing policies that reference the
removed action are NOT automatically invalidated. They remain in the store and
will fail at evaluation time. The auditor catches these by cross-referencing
the current schema against all policies, not by trusting validation status.

### Step 2: Authorization scope — overpermissive detection

**CRITICAL:** A bare `permit(principal, action, resource);` with zero scope
annotations and zero conditions authorizes EVERY request in the store. This is
the #1 Cedar security anti-pattern. If you see it, classify OVERPERMISSIVE
immediately — no further analysis needed for this policy.

If the policy is valid and schema-consistent, evaluate its authorization
scope. A policy that grants access too broadly is overpermissive.

**Rule 2a — Bare permit (CRITICAL overexposure):**
`permit(principal, action, resource);` with no type annotations on ANY scope
variable and no `when`/`unless` conditions. This matches every authorization
request — every principal, every action, every resource. The Cedar equivalent
of IAM `Principal:"*", Action:"*", Resource:"*"`. Classify as OVERPERMISSIVE.

**Rule 2b — Unscoped action/resource with broad principal (HIGH):**
A permit where `action` or `resource` lacks a type annotation, even if
`principal` is typed. Example:
`permit(principal: User, action, resource) when { principal.active };`
This grants ALL declared actions on ALL entity types to any User matching the
condition. The condition does not compensate for the unscoped action and
resource. Classify as OVERPERMISSIVE.

**Rule 2c — Trivially satisfiable condition (HIGH):**
A condition that is true for most or all principals at runtime, effectively
providing no restriction. Examples:
- `when { principal.accountStatus == "active" }` — virtually all users are
  active; this is an operational flag, not an access boundary.
- `when { principal has department }` — every user in the directory has a
  department attribute; `has` checks existence, not value.
Classify as OVERPERMISSIVE when paired with broad scope.

**Rule 2d — No `forbid` on sensitive actions (MEDIUM):**
If the policy set includes `permit` clauses for destructive actions
(`Delete*`, `Remove*`, `Destroy*`) but no corresponding `forbid` clause
restricting them to elevated principals, flag as OVERPERMISSIVE. A `forbid`
that blocks deletion unless `principal.role == "admin"` is the Cedar
equivalent of an IAM explicit Deny on non-admins.

**Rule 2e — Entity hierarchy breadth (MEDIUM):**
A policy using `principal in Group::"all-users"` grants access to every member
of the hierarchy, which may include service accounts, bots, and contractors.
Evaluate the `memberOfTypes` chain depth and breadth. If the hierarchy
includes broad groups, flag as OVERPERMISSIVE.

### Step 3: Policy store configuration gaps

If the policy passes Steps 0-2 (or Steps 0-2 findings are lower severity),
evaluate the store-level configuration for operational gaps.

**Config 3a — Validation mode OFF:**
`validationSettings.mode: OFF` disables all schema validation. Policies can
reference non-existent entities, actions, and attributes without detection.
This is a CONFIG_GAP regardless of whether current policies are clean — the
absence of validation means future policies will not be checked either.
Flag as CONFIG_GAP.

**Config 3b — No schema defined:**
A policy store with no schema cannot validate policies or enforce type
constraints. `IsAuthorized` calls may fail unpredictably. Flag as CONFIG_GAP.

**Config 3c — No identity source (for token-based authorization):**
If the application uses `IsAuthorizedWithToken` (Cognito or third-party IdP
integration) but no identity source is configured, token-based authorization
will fail. Flag as CONFIG_GAP.

**Config 3d — Policy count approaching quota:**
AVP allows up to 2,500 policies per store. A store with >2,000 policies is
approaching the quota — adding new policies may fail silently. Flag as
CONFIG_GAP (operational risk).

### Step 4: Template-linked policy audit

For `TEMPLATE_LINKED` policies, audit the **parent template** for scope and
conditions. The linked policy inherits all template clauses; the only
difference is the slot value (`?principal` → specific entity).

- If the template has a bare scope (`permit(?principal, action, resource)`),
  every linked policy inherits the bare scope → OVERPERMISSIVE.
- If the template has strong conditions, the linked policy is bounded by those
  conditions. Audit the condition strength per Step 2 rules.
- A template cannot be deleted while it has linked policies. Flag as an
  operational note if the template has >100 linked policies (management
  complexity).

### Step 5: Aggregation — worst finding wins

The final verdict is the **maximum severity** across all findings, where:
INVALID_POLICY > SCHEMA_MISMATCH > OVERPERMISSIVE > CONFIG_GAP > OK.

```text
verdict = max(step0_finding, step1_finding, step2_finding, step3_finding)
```

If no findings (all dimensions clean), the verdict is **OK**.

## Output format (per policy)

```text
POLICY: <policy-id or description>
VERDICT: INVALID_POLICY | SCHEMA_MISMATCH | OVERPERMISSIVE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its rule number>
FINDINGS:
  - [INVALID_POLICY] <finding description (Rule Na / Step N)>
  - [CONFIG_GAP] <finding description (Config Na)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — bare permit with validation OFF

```text
POLICY: pol-bare-permit-example
VERDICT: OVERPERMISSIVE
REASON: Policy is a bare permit(principal, action, resource) with no scope
constraints and no conditions — authorizes every request (Rule 2a).
Validation mode OFF compounds the risk (Config 3a).
FINDINGS:
  - [OVERPERMISSIVE] Bare permit matches all principals, actions, and
    resources with no conditions (Rule 2a)
  - [CONFIG_GAP] validationSettings.mode is OFF — schema validation disabled
    (Config 3a)
REMEDIATION:
  1. Replace the bare permit with a scoped policy:
     permit(principal: App::User, action: App::Action::"view",
       resource: App::Document)
     when { principal == resource.owner };
  2. Enable validation: update-policy-store --policy-store-id <id>
     --validation-settings mode=STRICT.
```

## Deep reference: Cedar authorization internals

Cedar internals (evaluation pipeline, entity hierarchy and the `in` operator, template linking, schema update semantics, size and store quotas) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for evaluation-order and quota detail.

## Expert edge cases

Expert edge cases (when/unless interaction, multiple when conjunctions, has operator, namespace scope, forbid as bare-permit safety net) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for the full gotcha catalog.

## Anti-Patterns — NEVER

- NEVER classify `permit(principal, action, resource);` (bare permit with no
  scope and no conditions) as anything other than OVERPERMISSIVE. This matches
  every authorization request — it is the most dangerous Cedar pattern.

- NEVER assume `validationSettings.mode: OFF` is safe. Policies referencing
  non-existent entities are silently accepted and cause unpredictable behavior
  at evaluation time (errors instead of DENY, or unexpected ALLOW). Always
  flag OFF as CONFIG_GAP.

- NEVER treat a `TEMPLATE_LINKED` policy as independently auditable. The linked
  policy inherits all conditions from its parent template. Always retrieve and
  audit the template via `get-template` — the linked policy text is opaque
  (the API returns the template ID + slot values, not expanded text).

- NEVER assume a `forbid` clause compensates for a bare `permit`. `forbid`
  blocks specific requests, but new actions/resources added to the schema are
  automatically covered by the bare `permit` and NOT by the existing `forbid`.
  The deny-list approach has an unbounded gap.

- NEVER evaluate schema consistency by looking at the policy alone. The schema
  is the source of truth. A policy may reference `Action::"DeletePhoto"` that
  was removed from the schema after the policy was created — this is a
  SCHEMA_MISMATCH even though the policy was valid at creation time.

- NEVER treat `principal in Group::"all-users"` as a scoped grant. Entity
  hierarchy traversal with `in` can match service accounts, bots, and
  contractors if they are members of the group. Evaluate the full membership
  chain, not just the group name.

- NEVER ignore `when`/`unless` reversal. `unless { principal.role == "admin" }`
  grants to everyone EXCEPT admins — the opposite of the likely intent. This
  is a logic error that produces inverted access decisions.

- NEVER assume that because validation is STRICT, all existing policies are
  schema-consistent. Validation runs at creation time only. Schema updates do
  not retroactively validate. Always cross-reference the current schema against
  all live policies.

- NEVER classify a policy with a type error (e.g., comparing `Long` with
  `String`) as SCHEMA_MISMATCH or OVERPERMISSIVE. A type error means the policy
  cannot be reliably evaluated — classify as INVALID_POLICY.

- NEVER assume `IsAuthorized` and `IsAuthorizedWithToken` are interchangeable.
  The former takes explicit entity data (including hierarchy); the latter
  extracts principal info from a Cognito/JWT token. Missing entity data in the
  former causes false DENY; missing token claims in the latter causes
  validation errors.

- NEVER recommend deleting a template that has linked policies. AVP rejects
  template deletion while linked policies exist. Always delete or unlink child
  policies first.

- NEVER treat Cedar namespace prefixes as interchangeable. `App::User` and
  `MyApp::User` are different entity types even if the local name is `User`.
  The full namespace-qualified name must match the schema.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`UpdatePolicy`, `DeletePolicy`, `PutSchema`, `UpdatePolicyStore`),
  the auditor MUST emit:
  `CONFIRM: About to <action> on policy <id> in store <store-id>. This
  affects <consequence>. Proceed? (yes/no)`.
  Do NOT execute the CLI command until the operator confirms.
- Policies are **not versioned** in AVP. `UpdatePolicy` replaces the entire
  policy text atomically — no diff, no staged rollout, no automatic rollback.
  The only recovery path is a manual backup of the prior policy text. ALWAYS
  capture the current policy via `get-policy` BEFORE any modification.
- Before enabling `STRICT` validation on a store currently in `OFF` mode,
  validate ALL existing policies against the schema first. Turning on STRICT
  does NOT retroactively validate, but any subsequent `UpdatePolicy` call
  on an invalid policy will fail with a validation error.
- Before updating the schema, list all policies that reference actions or
  entity types being removed. These policies will break silently at evaluation
  time. Update or delete them BEFORE updating the schema.
- Prefer additive changes (add a `forbid` clause, tighten a `when` condition)
  over destructive changes (delete a `permit`, remove a policy) — additive
  changes are reversible and do not risk breaking existing access patterns.

## Remediation guidance

### For INVALID_POLICY

1. Identify the specific parse or type error (line, operator, type mismatch).
2. Rewrite the policy text with correct Cedar syntax and types.
3. Update the policy:
   `aws verifiedpermissions update-policy --policy-store-id <store> --policy-id <id> --definition '{"static":"<corrected policy text>"}'`
4. If the error was caused by a schema change (attribute removed), either
   update the policy to not reference the removed attribute, or add the
   attribute back to the schema.

### For SCHEMA_MISMATCH

1. Identify the mismatched entity type, action, or attribute.
2. If the policy references an action not in the schema: either add the action
   to the schema (`put-schema`) or update the policy to reference a declared
   action.
3. If the policy references an entity type not in the schema: add the entity
   type to the schema, or update the policy's scope clause to use a declared
   type.
4. If the policy violates `appliesTo` constraints: update the policy's scope
   to match the action's `appliesTo.principalTypes` / `appliesTo.resourceTypes`.

### For OVERPERMISSIVE

1. Replace bare permits with scoped policies:
   ```cedar
   permit (
     principal: App::User,
     action: App::Action::"view",
     resource: App::Document
   )
   when { principal == resource.owner };
   ```
2. Add type annotations to unscoped `action` and `resource` variables.
3. Replace trivially satisfiable conditions with meaningful access boundaries.
4. Add `forbid` clauses for destructive actions:
   ```cedar
   forbid (
     principal: App::User,
     action: App::Action::"delete",
     resource: App::Document
   )
   unless { principal.role == "admin" };
   ```
5. Test the remediated policy with `is-authorized` before deploying.

### For CONFIG_GAP

1. Enable strict validation:
   `aws verifiedpermissions update-policy-store --policy-store-id <store> --validation-settings mode=STRICT`
2. If no schema exists, author and put a schema:
   `aws verifiedpermissions put-schema --policy-store-id <store> --definition file://schema.json`
3. After enabling validation, run a full policy audit (Steps 0-4) — existing
   policies may now reveal INVALID_POLICY or SCHEMA_MISMATCH findings that
   were hidden by the OFF mode.
4. Configure identity sources if using `IsAuthorizedWithToken`.

### For OK

1. No remediation required for the current posture.
2. Recommend periodic re-audit after any schema update (schema changes do not
   retroactively validate existing policies).
3. Recommend adding `forbid` clauses for defense-in-depth on sensitive actions.

## Recent AWS features (2024-2026)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand to check what changed in the last 24 months.

## AWS documentation

- **Amazon Verified Permissions User Guide** — https://docs.aws.amazon.com/verifiedpermissions/latest/userguide/
- **Cedar Policy Language Reference** — https://docs.cedarpolicy.com/
- **AVP Security** — https://docs.aws.amazon.com/verifiedpermissions/latest/userguide/security.html
- **AVP API Reference** — https://docs.aws.amazon.com/verifiedpermissions/latest/apireference/
- **AVP CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/verifiedpermissions/
- **Cedar policy validation** — https://docs.aws.amazon.com/verifiedpermissions/latest/userguide_policy-validation.html

## References (load on demand)

- [Diagnostic commands](references/diagnostic-commands.md) — live-account pre-flight checks (policy store metadata gate)
- [Advanced patterns](references/advanced-patterns.md) — quantitative risk thresholds, Cedar evaluation heuristics, authorization internals, expert edge cases, recent AWS features (2024-2026)
