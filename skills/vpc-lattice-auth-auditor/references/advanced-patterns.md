# Advanced Patterns — VPC Lattice Auth Auditor

Deep reference content moved verbatim from `vpc-lattice-auth-auditor/SKILL.md`. Loaded on demand;
see SKILL.md for the condensed core and its quick navigation.

## Step 1 rationale — why NO_AUTH_POLICY outranks a permissive policy

This step is evaluated first because it represents a complete absence of
resource-based access control. Even a permissive auth policy
(Principal: "*") is better than no auth policy — at least the policy is an
explicit decision. NO_AUTH_POLICY means the operator may not know access is
unrestricted.

## Rule 5d rationale — cross-account invoke is always CONFIG_GAP

**Important:** Rule 5d produces CONFIG_GAP even with a STRONG condition
because cross-account invoke access is inherently an external trust
dependency. A policy edit, a deleted role, or a compromised external account
widens exposure. The STRONG condition narrows the blast radius but does not
eliminate the cross-account dependency.

## Edge-case handling catalog

- **Partially malformed auth policy.** If the JSON parses but individual
  statements are missing `Effect`, `Principal`, or `Action`/`NotAction`,
  classify each valid statement normally and emit an ERROR note for each
  malformed one. Do NOT classify the entire network as ERROR when one
  statement is broken.

- **Conflicting Allow and Deny.** A Deny statement blocks the same
  principal/action as an Allow. Deny wins. However, a Deny on
  `aws:SecureTransport: false` with `Principal: "*"` blocks non-TLS access
  but does NOT restrict TLS access from a wildcard principal — the wildcard
  Invoke is still PUBLIC_SERVICE_NETWORK.

- **Statement with `Principal: "*"` AND same-account principals.** Classified
  by the **widest** principal — WILDCARD_PRINCIPAL. Same-account does not
  dilute the wildcard.

- **NotPrincipal in an Allow.** `NotPrincipal` grants to every principal
  EXCEPT the listed one. Treat any NotPrincipal in an Allow as
  WILDCARD_PRINCIPAL.

- **Empty auth policy (no statements).** An auth policy with an empty
  `Statement` array means NO principal is allowed — including the owning
  account. This effectively denies all invocation. Output VERDICT: ERROR,
  REASON: "Auth policy has no statements — all invocation is denied. Verify
  this is intentional."

## Expert knowledge — non-obvious VPC Lattice behaviors

These are operational gotchas and silent failures that are NOT in AWS docs
or require hard-won production experience to discover.

- **Auth policy absence is DEFAULT-OPEN.** VPC Lattice service networks are
  created WITHOUT an auth policy. Unlike KMS or S3, no auth policy means ANY
  resource in an associated VPC can invoke. Operators assume "no policy =
  locked down." It means the opposite.

- **`vpc-lattice:Invoke` is the only auth-policy action controlling
  invocation.** Management actions (CreateService, PutAuthPolicy) are
  IAM-gated, not auth-policy-gated. An auth policy with `vpc-lattice:*`
  grants Invoke but management actions still require IAM.

- **VPC association is ROUTING, not AUTH.** Associating a VPC enables DNS
  resolution and routing. It does NOT restrict invocation — any resource in
  the associated VPC can route to services. Treating VPC association as a
  security boundary is a fundamental misread.

- **RAM sharing grants VISIBILITY, not INVOCATION.** The consumer needs BOTH
  the auth policy to Allow them AND IAM `vpc-lattice:Invoke`. Without an
  auth policy, the RAM share + VPC association is sufficient (no
  resource-based gate).

- **Cross-account auth-policy evaluation is INTERSECTION-based.** Both auth
  policy AND caller's IAM must Allow (same as S3). Same-account: EITHER
  suffices (union) — but only if an auth policy exists.

- **IP target groups route to arbitrary IPs.** Unlike INSTANCE targets
  (bound to VPC ENIs), IP targets point anywhere — cross-VPC, cross-account,
  on-premises. Targets outside the VPC CIDR are a potential exfiltration path.

- **Auth policies are NOT versioned.** `PutAuthPolicy` replaces the entire
  document atomically — no diff, no staged rollout, no rollback API.

- **Service DNS names resolve in ALL associated VPCs.** A service private to
  one account is DNS-resolvable from a consumer account's VPC if the network
  is RAM-shared. DNS visibility is NOT scoped by account.

- **`aws:SourceVpc`/`aws:SourceVpce` are the strongest conditions.** Set by
  VPC endpoint infrastructure; caller cannot forge. `aws:SourceAccount` is
  strong. `aws:SourceIp` is architecturally unreliable for Lattice (see
  anti-patterns).

- **`PutAuthPolicy` is eventually consistent.** GetAuthPolicy may return
  stale results for seconds after a write. No state-transition event exists.

- **Auth policy has no DryRun or validation API.** You cannot validate a
  policy document before putting it. A syntax-valid but semantically broken
  policy (e.g., denying the owning account) takes effect immediately with
  no preview. Always test in a non-production service network first.

- **Deny statements override Allow in the same auth policy.** A Deny on
  `Principal: "*"` with `aws:SecureTransport: false` blocks non-TLS but does
  NOT restrict TLS from a wildcard principal — the Allow still applies for
  TLS traffic. Deny+Allow overlap on Invoke requires explicit Deny of the
  principal/action, not a condition-based Deny.

## Deep reference — Lattice authorization internals

### Authorization evaluation pipeline (condensed)

Request flow: routing (associated VPC resolves DNS) → auth policy (if absent,
default-open ALLOW) → IAM intersection (cross-account) or union (same-account)
→ target forwarding (security group on VPC association is last network gate).

### Cross-account intersection model (condensed)

Cross-account invocation requires BOTH the auth policy AND the caller's IAM
identity-based policy to Allow (intersection, same as S3). Same-account
callers need EITHER to Allow (union) — but only if an auth policy exists.
Without an auth policy, only IAM matters (default-open). **The caller's IAM
identity-based policy is a mandatory audit dimension.**

Concrete verification: for each cross-account principal granted Invoke in
the auth policy, run:
`aws iam simulate-principal-policy --policy-source-arn <caller-role-arn>
--action-names vpc-lattice:Invoke --resource-arns <sn-arn>`
If `EvalDecision` is `allowed`, the intersection permits invocation. If
`implicitDeny`, the auth-policy Allow is inert — the caller CANNOT invoke
despite being listed.

### Auth policy vs IAM policy scope (key differences)

Auth policy: attached to service network/service, default NOT_SET (absent =
open), no versioning (atomic replace). IAM identity-based policy: attached
to role/user, default deny, managed policies support 10 versions.
