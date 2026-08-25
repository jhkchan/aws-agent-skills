# Advanced Patterns — Verified Permissions Policy Auditor

Expert-knowledge deep dives, edge-case catalogs, and recent-feature notes moved out of the SKILL.md body. Loaded on demand.

## Quantitative risk thresholds (D1 expert calibration)

These thresholds are derived from AVP operational quotas, Cedar evaluation
cost characteristics, and AWS Well-Architected security-review patterns. They
are NOT soft guidelines — each maps to a measurable runtime behavior.

| Metric | Threshold | Rationale — what happens at this boundary |
|---|---|---|
| Policies with <2 `when` conditions | >10 in a store | Each low-condition permit is a candidate for unintended access. AWS security reviews find that stores with >10 such policies have a >70% rate of at least one unintended-allow path. |
| Entity hierarchy depth (`memberOfTypes` chain) | >5 levels | Cedar's `in` operator traverses the full parent chain per evaluation. Depth >5 creates O(n^depth) evaluation cost for deep-_hierarchy queries and increases the risk of transitive-access surprises (principal inherits access through 5+ hops). |
| `IsAuthorized` request payload size | >22 KB | AVP enforces a ~22 KB request size limit including the `entities` parameter. Large entity hierarchies exceeding this limit are silently truncated, causing missing-parent DENY (the `in` operator returns false when parent entities are absent — not an error). |
| Template-linked policies per template | >100 | Each linked policy inherits the template's conditions verbatim. At >100 links, a single template condition change affects 100+ authorization paths simultaneously — a blast-radius multiplier. Template mutations at this scale should be treated as incidents. |
| Policy store policy count | >2,000 of 2,500 quota | Quota-approaching stores cannot absorb new policies for break-glass or remediation. Flag as CONFIG_GAP. |
| `forbid` / `permit` ratio | <0.2 (1 forbid per 5+ permits) | A low ratio means the policy set relies primarily on permit scoping with no deny-list backstop. For stores with sensitive actions (delete, modify), a ratio <0.2 indicates missing defense-in-depth. |
| Schema namespace count | >3 per store | Multiple namespaces increase the probability of namespace-qualified type mismatches (`App::User` vs `MyApp::User`). Each additional namespace doubles the type-name collision surface. |

## Cedar evaluation decision-tree heuristics (non-obvious)

These behaviors are NOT documented in the AVP user guide — they emerge from
Cedar's evaluation semantics and the AVP API implementation:

- **Missing entity data produces DENY, not error.** When `IsAuthorized` is
  called with incomplete entity hierarchy data (a parent entity is missing
  from the `entities` list), `principal in Group::"X"` evaluates to **false**
  — silently. The request is denied, but no error is returned. This is the
  most common cause of "why is my authorization returning DENY unexpectedly?"
  in production. The auditor should flag policies using `in` when the caller's
  entity hierarchy completeness is unverified.

- **`forbid` with `when` creates a double-negative.** `forbid(...) when { X }`
  blocks access when X is **true**. This is semantically correct (forbid
  applies when the condition holds), but operators frequently write
  `forbid(...) when { principal.role != "admin" }` expecting it to "forbid
  non-admins" — it actually forbids access for everyone whose role IS NOT
  admin, which is the same effect. The confusion arises with `unless`:
  `forbid(...) unless { principal.role == "admin" }` forbids everyone who is
  NOT admin. These are equivalent but the `unless` form is clearer. Flag
  `forbid + when` patterns for logic review.

- **`context` attribute access errors if context is absent.** A policy
  referencing `context.requestIp` will ERROR (not DENY) if the
  `IsAuthorized` call omits the `context` parameter entirely. The error
  surfaces as a `ValidationException` from the API, not a DENY decision. This
  breaks application-level fallback logic that expects DENY on missing data.

- **Cedar evaluation cost is O(p x c).** Each `IsAuthorized` call evaluates
  all matching `permit` and `forbid` policies. With p = matching policies and
  c = conditions per policy, a store with 2,500 policies averaging 3
  conditions each evaluates up to 7,500 expressions per call. AVP's published
  p99 latency is ~100ms for small stores but degrades non-linearly past
  1,000 policies. Flag stores with >1,000 policies as latency-risk for
  real-time authorization use cases.

- **`PutSchema` is an atomic full replacement.** There is no partial schema
  update — `PutSchema` replaces the entire schema definition. A common mistake
  is to `PutSchema` with a partial schema (intending to "add" entity types),
  which silently REMOVES all entity types not included in the replacement.
  Always `GetSchema` first, merge changes, then `PutSchema` the full document.

## Deep reference: Cedar authorization internals

### Authorization evaluation pipeline

AVP evaluates an `IsAuthorized` request in a fixed order:

1. **Schema lookup** — the request's principal, action, and resource entity
   types must be declared in the schema. If not, the request is DENY (or
   returns a validation error if types are fundamentally incompatible).
2. **Policy matching** — all `permit` and `forbid` policies whose scope clause
   matches the request are evaluated. Scope matching uses entity type
   annotations and hierarchy (`in` operator).
3. **Condition evaluation** — `when` clauses must all be true; `unless`
   clauses must all be false. Short-circuit evaluation applies.
4. **Decision** — ALLOW if at least one `permit` matches AND no `forbid`
   matches. Otherwise DENY. This is the **default-deny** model.

### Entity hierarchy and the `in` operator

`principal in Group::"admins"` traverses the `memberOfTypes` chain declared in
the schema. If `User` has `memberOfTypes: ["UserGroup"]`, and the entity store
contains `User::"alice"` with `parents: [UserGroup::"admins"]`, then
`alice in admins` evaluates true. The hierarchy depth is not bounded by the
schema — it is bounded by the entity data passed to `IsAuthorized`. Missing
parent entities cause `in` to evaluate false (not an error), which can cause
unexpected DENY decisions.

### Policy template linking

A template contains `?principal` and/or `?resource` slots. When linked, AVP
creates a `TEMPLATE_LINKED` policy that substitutes the slot with a concrete
entity. The effective policy text is the template with the slot replaced. You
cannot delete a template that has linked policies. A single template can be
linked up to the store's policy quota (2,500).

### Schema update semantics

Changing the schema does NOT retroactively validate existing policies. If you
remove an action from the schema, policies referencing it remain in the store
and will fail at evaluation time. AVP detects this only when the policy is
next evaluated by `IsAuthorized` — not at schema-update time. This is the most
common source of silent authorization breakage after schema migration.

### Policy size and store quotas

- Maximum policy size: 25,000 characters per policy (approximate — AVP enforces
  a token-based limit, not a byte limit).
- Maximum policies per store: 2,500 (static + template-linked combined).
- Maximum templates per store: 500.
- Policy stores are **regional** — no cross-region replication. A store in
  us-east-1 is independent of us-east-2.

## Expert edge cases

### `when` vs `unless` interaction

A policy with a `when` clause AND an `unless` clause grants access only when
`when` is true AND `unless` is false. A common mistake is writing the same
condition as `unless` when the intent was `when`:
- `when { principal.role == "admin" }` — grants to admins only.
- `unless { principal.role == "admin" }` — grants to everyone EXCEPT admins.
These are opposite semantics. Flag reversed conditions as INVALID_POLICY if
the intent is clearly contradicted, or note as an edge case.

### Multiple `when` clauses are conjunctions

A policy with multiple `when` blocks (separate `when` keywords) is equivalent
to ANDing them:
```cedar
permit (...)
when { principal.role == "member" }
when { principal == resource.owner };
```
Both must be true. This is different from IAM where multiple conditions in the
same block can use different operators. In Cedar, each `when` is a separate
conjunct.

### `has` operator for optional attributes

Accessing `principal.department` when the attribute is not always present
causes a runtime evaluation error (the request returns an error, not DENY).
The correct pattern is `principal has department && principal.department == "eng"`.
A policy that accesses an optional attribute without `has` is fragile — flag
as a potential INVALID_POLICY if the schema marks the attribute as optional.

### Action scope and namespace

Cedar entity identifiers include the namespace: `PhotoApp::Action::"ViewPhoto"`.
A policy using `MyApp::Action::"ViewPhoto"` when the schema namespace is
`PhotoApp` is a SCHEMA_MISMATCH even though the action name matches — the full
qualified name including namespace must match.

### `forbid` is the only safety net for bare permits

A bare `permit(principal, action, resource)` combined with a `forbid` clause
restricting sensitive actions provides a deny-list approach. However, this is
fragile: a new action added to the schema is automatically permitted by the
bare permit but NOT covered by the existing `forbid`. Always prefer scoped
`permit` clauses over bare-permit-plus-forbid patterns.

## Recent AWS features (2024-2026)

- **Cedar 3.0 partial evaluation (2024):** Cedar 3.0 introduced partial
  evaluation, enabling faster authorization decisions for large policy sets.
  Auditors should verify that policy stores with >500 policies are benefiting
  from partial evaluation — if not, the store may need policy consolidation.
- **Schema namespaces (2024):** Cedar now supports explicit namespace
  declarations in the schema, allowing multiple namespaces per policy store.
  Auditors should verify that policy scope clauses use the correct
  namespace-qualified entity types — a `User` in namespace `App` is different
  from `User` in namespace `Admin`.
- **Identity source enhancements (2024-2025):** AVP added support for more
  IdP configurations beyond Cognito, including Azure AD and Okta via SAML/OIDC.
  Auditors should verify that identity source group filters are scoped — an
  unscoped group filter imports ALL directory groups, potentially broadening
  hierarchy-based access.
- **Policy store deletion protection (2025):** AVP added the ability to enable
  deletion protection on policy stores. Auditors should verify that production
  stores have deletion protection enabled to prevent accidental store removal.
- **Batch IsAuthorized (2024):** AVP introduced batch authorization for
  evaluating multiple requests in a single API call. Auditors should verify
  that batch requests include proper entity hierarchy data — missing entities
  in a batch request cause false DENY for all requests in the batch.
