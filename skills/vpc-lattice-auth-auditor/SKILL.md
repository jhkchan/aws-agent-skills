---
name: vpc-lattice-auth-auditor
description: Audits VPC Lattice service networks for auth-policy absence (default-open posture), public Principal:"*" Invoke grants, NotAction inverse-wildcard traps, cross-account principal exposure without strong conditions, target group security (IP targets to untrusted CIDRs, type-mismatch health checks), cross-account RAM share coverage, routing-rule catch-all exposure, and service-level auth-policy overrides that silently bypass network-level guards. Emits a deterministic verdict (NO_AUTH_POLICY | PUBLIC_SERVICE_NETWORK | CONFIG_GAP | OK) per service network with enumerated findings and CLI remediation. Use when reviewing VPC Lattice auth policies, checking service-network access scope, validating cross-account sharing, auditing target group security, or hardening service-network posture before production deployment.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline auth-policy-document classification. Live-account audits use aws vpc-lattice get-auth-policy, aws vpc-lattice list-service-networks, aws vpc-lattice list-target-groups, and aws ram list-resources (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  verdict_shape: NO_AUTH_POLICY | PUBLIC_SERVICE_NETWORK | CONFIG_GAP | OK
  when_to_use: Reviewing a VPC Lattice service network auth policy before production deployment, checking for absent auth policy (default-open posture), auditing public Principal:"*" Invoke grants, validating cross-account RAM share coverage, inspecting target group security, or hardening service-network access scope.
  activation_triggers: audit this VPC Lattice service network, is my service network public, check lattice auth policy, vpc lattice cross-account access, lattice target group security, lattice RAM share audit, no auth policy on service network, vpc-lattice:Invoke exposure
  invocation_schema: 'Input shape (one of): (a) auth-policy JSON + optional metadata (associations, services, target groups, RAM shares) for offline classification; (b) service-network identifier (sn-xxx) for live-account audit. Output shape: { SERVICE_NETWORK, VERDICT, REASON, FINDINGS[], REMEDIATION } where VERDICT ∈ { NO_AUTH_POLICY, PUBLIC_SERVICE_NETWORK, CONFIG_GAP, OK, ERROR }.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: VPC Lattice, auth policy, service network, vpc-lattice:Invoke, Principal:"*", cross-account, RAM share, target group, routing rule, resource policy, NotAction, service auth policy, lattice security, application networking, invoke access, auth policy override
  tags: vpc-lattice, security, auth-policy, service-network, cross-account, ram, target-group, routing, audit
---

# VPC Lattice Auth Auditor

## Mindset

**One-line takeaway:** the verdict is the **worst** finding across all
dimensions, and VPC Lattice has a trap unique among AWS resource-based
policies — **absence of an auth policy is the default state, and it means
"open within associated VPCs," not "no access."**

VPC Lattice is the application-networking layer between your services. Its
auth model differs from KMS or S3 in a critical way:
- **Auth policy absence is the DEFAULT.** A new service network has NO
  resource-based auth policy. Without one, any resource in an associated VPC
  can invoke any service in the network — IAM identity-based policy alone is
  the only gate.
- **`vpc-lattice:Invoke` is the blast-radius action.** One permission grants
  the ability to call any service in the network. Unlike `kms:Decrypt` (data
  exposure), Invoke grants **service-call access** — the caller can hit every
  endpoint, API, and microservice behind the network.
- **Service-level auth policy overrides network-level.** A service can carry
  its OWN auth policy that silently replaces the service network's. A secure
  network-level policy is bypassed by a permissive service-level override.

## Quick-start (90-second audit)

For first-pass triage — full classification logic, edge cases, and remediation below.

1. **Auth policy present?** `NOT_SET` → **NO_AUTH_POLICY** (default-open, worst verdict). Stop.
2. **Any `Principal: "*"` with Invoke or `vpc-lattice:*` or `NotAction`?** → **PUBLIC_SERVICE_NETWORK**. Stop.
3. **Any cross-account principal with Invoke?** → **CONFIG_GAP** (always, even with strong conditions). Stop.
4. **IP targets outside VPC CIDR, RAM share without scoped policy, or permissive service-level override?** → **CONFIG_GAP**.
5. **All dimensions clean?** → **OK**.

Worst finding wins: NO_AUTH_POLICY > PUBLIC_SERVICE_NETWORK > CONFIG_GAP > OK.

## Quick reference — verdict matrix

| Condition | Verdict | Rule |
|---|---|---|
| No auth policy on service network (and no service-level policy) | **NO_AUTH_POLICY** | Step 1 |
| Auth policy + `Principal: "*"` + Invoke/vpc-lattice:*/* + no strong condition | **PUBLIC_SERVICE_NETWORK** | Rule 5a |
| Auth policy + `Principal: "*"` + NotAction (inverse wildcard) | **PUBLIC_SERVICE_NETWORK** | Rule 5b |
| Auth policy + cross-account + Invoke + no condition | **CONFIG_GAP** | Rule 5c |
| Auth policy + cross-account + Invoke + STRONG condition | **CONFIG_GAP** | Rule 5d |
| Auth policy + IP target group + targets outside VPC CIDR | **CONFIG_GAP** | Step 6 |
| Auth policy + RAM share to external account + no scoped policy | **CONFIG_GAP** | Step 7 |
| Auth policy + same-account + Invoke + STRONG condition + clean targets | **OK** | Step 9 |

See the ordered steps below for edge cases. Deep VPC Lattice authorization
internals are in the [Deep reference](#deep-reference-lattice-authorization)
section.

## Pre-flight: service-network metadata gate (run before auth-policy classification)

Before evaluating the auth policy, classify the service network itself.

Live-account pre-flight checks (run before auth-policy classification) — moved verbatim.
Full detail: [Diagnostic commands](references/diagnostic-commands.md).

| Attribute | Value | Effect on audit |
|---|---|---|
| Auth policy state | `NOT_SET` | **No auth policy.** Default-open: any resource in an associated VPC can invoke services. Jump to Step 1. |
| Auth policy state | `ACTIVE` | Proceed with full audit. |
| Service count | 0 | Empty service network — no services to invoke. Note as operational but not a security verdict driver. |
| VPC associations | 0 | No VPCs associated — the service network is not routable. Low risk but flag as orphaned. |
| RAM shares | External account | Cross-account exposure — check auth policy covers the consumer account. |
| RAM shares | None | No cross-account sharing. Proceed with same-account audit. |

Malformed auth-policy ERROR output (pre-flight gate) — moved verbatim.
Full detail: [Error handling](references/error-handling.md).

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Critical classification rules (see Expert Knowledge for depth)

- **No auth policy = DEFAULT-OPEN**, not locked down. Any resource in an
  associated VPC can invoke. This drives Step 1.
- **NotAction in an Allow = inverse wildcard.** Invoke is included. Treat
  as INVOKE_ACCESS. This drives Rule 5b.
- **Cross-account Invoke is ALWAYS CONFIG_GAP**, even with a STRONG
  condition. Same-account + STRONG = OK (Rule 5h). This drives Step 5.
- **Service-level auth policy silently overrides network-level.** Always
  enumerate service-level policies independently. This drives Step 8.
- **CloudTrail does NOT log `vpc-lattice:Invoke`** data-plane events.
  Forensics need VPC Flow Logs, not CloudTrail.
- **The `Resource` element is effectively ignored** in Lattice auth policies.
  Use Principal and Condition to scope, never Resource.

Full rationale and additional non-obvious behaviors in
[Expert knowledge](#expert-knowledge-non-obvious-vpc-lattice-behaviors)
at the end.

### Step 1: Auth-policy presence (highest priority — default-open exposure)

If the service network has NO auth policy (`state: NOT_SET`) and NO
service-level auth policy:

- **NO_AUTH_POLICY.** The service network is default-open. Any resource in
  an associated VPC can invoke any service. If the network is shared
  cross-account via RAM, the consumer account's VPC resources can also
  invoke. This is the single most common VPC Lattice security finding.

Step 1 rationale — why NO_AUTH_POLICY outranks a permissive policy — moved verbatim.
Full detail: [Advanced Patterns](references/advanced-patterns.md).

### Step 2: Principal scope classification

For each `Effect: Allow` statement in the auth policy, classify the principal:

- **WILDCARD_PRINCIPAL** — Principal is `"*"`, `{"AWS": "*"}`, or any
  construct resolving to all principals.

- **CROSS_ACCOUNT** — Principal includes an ARN whose 12-digit account ID
  differs from the service network's owning account. Example: service
  network in `111111111111` with principal
  `arn:aws:iam::222222222222:role/consumer-app`.

- **SAME_ACCOUNT** — All principals share the owning account ID.

A statement with BOTH same-account and cross-account principals is
classified by the **widest** scope — CROSS_ACCOUNT.

### Step 3: Action danger classification

Classify the action set in each Allow statement by danger level:

| Danger level | Actions | Why |
|---|---|---|
| **INVOKE_ACCESS** | `vpc-lattice:Invoke`, `vpc-lattice:*`, `*`, NotAction in Allow | Can call any service in the network. Invoke is the blast-radius action — one permission, full service-call access. |
| **CONTROL_ACCESS** | `vpc-lattice:PutAuthPolicy`, `vpc-lattice:DeleteServiceNetwork`, `vpc-lattice:DeleteService` | Can modify the auth policy or delete the network. Lower severity in auth-policy context (these are also IAM-gated), but flag as a privilege risk. |
| **METADATA** | `vpc-lattice:Get*`, `vpc-lattice:List*` | Read-only — enumerate services, target groups, associations. Low severity. |

**NotAction in an Allow statement** is an inverse wildcard — it grants
every action EXCEPT the listed ones. Treat as INVOKE_ACCESS because
`vpc-lattice:Invoke` is automatically included unless explicitly listed in
the NotAction array.

### Step 4: Condition strength evaluation

**STRONG conditions (downgrade severity by noting the restriction):**
- `aws:SourceVpc` with `StringEquals` — request must originate from the
  named VPC. Set by VPC endpoint infrastructure; caller cannot forge.
- `aws:SourceVpce` with `StringEquals` — request must originate from the
  named VPC endpoint. Tighter than SourceVpc.
- `aws:SourceAccount` with `StringEquals` — request must originate from the
  named account. Set by the calling AWS service.
- `aws:SourceArn` with `StringEquals`/`StringLike` — request must originate
  from the named resource ARN.

**WEAK conditions (do NOT treat as a restriction):**
- `aws:SourceIp` / `aws:SourceIp` containing `0.0.0.0/0` — bypassable by
  callers who control egress (NAT, proxy, VPN).
- `aws:Referer`, `aws:UserAgent` — trivially forgeable.
- Any condition wrapped in `IfExists` — weakens the assertion.

### Step 5: Cross-reference — the verdict matrix

**CROSS_ACCOUNT INVOKE GATE — evaluate BEFORE the matrix:**
If ANY Allow statement grants `vpc-lattice:Invoke` (or `vpc-lattice:*` or
`*` or `NotAction`) to a principal whose 12-digit account ID DIFFERS from
the service network's owning account, that statement's finding is
**CONFIG_GAP** — unconditionally, regardless of any Condition block
(`aws:SourceAccount`, `aws:SourceArn`, `aws:SourceVpc`, or any other key).
This is a hard short-circuit. The STRONG condition narrows the blast radius
but cannot eliminate the cross-account trust dependency. Only SAME_ACCOUNT
and WILDCARD principals proceed to the matrix below.

Combine principal scope (Step 2), action danger (Step 3), and condition
strength (Step 4). Apply in order — first matching row determines the
finding severity for that statement:

| # | Principal | Action danger | Condition | Finding | Rule |
|---|---|---|---|---|---|
| 5a | WILDCARD | INVOKE_ACCESS | None/weak | **PUBLIC_SERVICE_NETWORK** | Rule 5a: any AWS principal can invoke services |
| 5b | WILDCARD | INVOKE_ACCESS (via NotAction) | None/weak | **PUBLIC_SERVICE_NETWORK** | Rule 5b: NotAction inverse wildcard silently grants Invoke |
| 5c | CROSS_ACCOUNT | INVOKE_ACCESS | None/weak | **CONFIG_GAP** | Rule 5c: cross-account invoke with no condition |
| 5d | CROSS ACCOUNT | INVOKE_ACCESS | STRONG | **CONFIG_GAP** | Rule 5d: cross-account invoke, condition-restricted but still external |
| 5e | WILDCARD | CONTROL_ACCESS | None/weak | **CONFIG_GAP** | Rule 5e: wildcard policy mutation — any principal can replace the auth policy |
| 5f | CROSS_ACCOUNT | CONTROL_ACCESS | None/weak | **CONFIG_GAP** | Rule 5f: cross-account policy mutation |
| 5g | WILDCARD or CROSS | METADATA | None/weak | **CONFIG_GAP** | Rule 5g: metadata enumeration by external principals |
| 5h | SAME_ACCOUNT | INVOKE_ACCESS | STRONG | **OK** (for this dimension) | Rule 5h: same-account scoped with strong condition |
| 5i | SAME_ACCOUNT | INVOKE_ACCESS | None | **CONFIG_GAP** | Rule 5i: same-account invoke with no condition — fragile |

Rule 5d rationale — cross-account invoke is always CONFIG_GAP — moved verbatim.
Full detail: [Advanced Patterns](references/advanced-patterns.md).

### Step 6: Target group security evaluation

Evaluate each target group associated with the service network's services:

- **INSTANCE targets in the owning VPC** → OK for this dimension.
- **INSTANCE targets in a different VPC** → CONFIG_GAP (cross-VPC routing
  without explicit peering validation).
- **IP targets within the owning VPC CIDR** → OK.
- **IP targets outside the owning VPC CIDR** (cross-VPC, cross-account,
  on-premises, or `0.0.0.0/0`) → **CONFIG_GAP**. IP targets to arbitrary
  addresses are a potential data-exfiltration path or routing black hole.
- **LAMBDA targets** → OK for network security (Lambda has its own
  resource-policy gate). Note as operational — Lambda invoke permissions
  are governed by the function's resource policy, not the target group.
- **ALB targets** → OK (ALB has its own security groups). Note that the ALB
  listener must match the Lattice forwarding protocol.

### Step 7: Cross-account RAM share evaluation

If the service network is shared via AWS RAM:

- **RAM share + NO auth policy** → the finding is already NO_AUTH_POLICY
  (Step 1), but escalate the REASON to note cross-account exposure: consumer
  VPC resources can invoke services with no resource-based gate.
- **RAM share + auth policy with the consumer account as named principal +
  STRONG condition** → OK for this dimension (scoped cross-account access).
- **RAM share + auth policy WITHOUT the consumer account** → CONFIG_GAP
  (the share grants visibility, but the auth policy does not explicitly
  Allow the consumer — this may be intentional or an oversight).
- **RAM share + auth policy with `Principal: "*"`** → already
  PUBLIC_SERVICE_NETWORK (Rule 5a), but note the RAM share compounds
  exposure.

### Step 8: Service-level auth policy override check

If ANY service in the network has its OWN auth policy:

- Evaluate the service-level policy INDEPENDENTLY using Steps 2-5.
- A service-level policy that is MORE permissive than the network-level
  policy produces a separate finding for that service.
- A service-level policy that is MORE restrictive than the network-level
  policy is fine (defense in depth) — note as OK for that service.
- The overall verdict is the **worst** finding across the network-level
  policy AND all service-level policies.

### Step 9: Aggregation — worst finding wins

```text
verdict = max(all_statement_findings, target_group_finding, ram_share_finding, service_override_finding)
```

Where NO_AUTH_POLICY > PUBLIC_SERVICE_NETWORK > CONFIG_GAP > OK.

If no findings (auth policy present, properly scoped, target groups clean,
no cross-account exposure, no service overrides), the verdict is **OK**.

## Output format (per service network)

```text
SERVICE NETWORK: <sn-id>
VERDICT: NO_AUTH_POLICY | PUBLIC_SERVICE_NETWORK | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its rule number>
FINDINGS:
  - [NO_AUTH_POLICY] <finding description>
  - [PUBLIC_SERVICE_NETWORK] <finding description (Rule Na)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — public service network with wildcard Invoke

```text
SERVICE NETWORK: sn-0b2c3d4e5
VERDICT: PUBLIC_SERVICE_NETWORK
REASON: Auth policy Statement "OpenInvoke" grants vpc-lattice:* to
Principal "*" with no restrictive condition — any AWS principal can invoke
every service in the network (Rule 5a).
FINDINGS:
  - [PUBLIC_SERVICE_NETWORK] Principal: "*" + vpc-lattice:* + no condition (Rule 5a)
  - [CONFIG_GAP] IP target group tg-0b2c has target 203.0.113.50 outside VPC CIDR 10.0.0.0/16 (Step 6)
REMEDIATION:
  1. Replace Principal: "*" with specific same-account role ARNs.
  2. Add aws:SourceVpc or aws:SourceAccount condition to scope invocation.
  3. Remove the external IP target or verify it is an intentional on-premises endpoint.
```

## Edge-case handling

Edge-case handling catalog — moved verbatim.
Full detail: [Advanced Patterns](references/advanced-patterns.md).

### Worked example — partially malformed auth policy

Worked example — partially malformed auth policy — moved verbatim.
Full detail: [Worked examples](references/worked-examples.md).

API errors during live-account audit; CONFIG_GAP remediation ticket rule — moved verbatim.
Full detail: [Error handling](references/error-handling.md).

## Anti-Patterns — NEVER

- NEVER classify a service network with NO auth policy as OK or CONFIG_GAP.
  Absence of an auth policy is the DEFAULT-OPEN state — any resource in an
  associated VPC can invoke services. This is NO_AUTH_POLICY, the highest-
  concern verdict. Operators assume "no policy = locked down." It means the
  opposite.

- NEVER treat VPC association as a security boundary. VPC association
  enables routing and DNS resolution. It does NOT restrict which resources
  can invoke services. A service network with 10 VPCs associated and no
  auth policy is open to ALL resources in ALL 10 VPCs.

- NEVER assume the service network auth policy covers all services. A
  service with its OWN auth policy silently overrides the network policy. A
  network-level audit that skips service-level policies misses the bypass.
  Always enumerate service-level policies.

- NEVER classify `Principal: "*"` with `vpc-lattice:Invoke` or `vpc-lattice:*`
  as CONFIG_GAP. This is PUBLIC_SERVICE_NETWORK — any AWS principal can
  invoke every service. CONFIG_GAP implies a scoped issue, not an open
  service network.

- NEVER ignore `NotAction` in an Allow auth policy. `NotAction` is an inverse
  wildcard that grants every action except the listed ones. Since
  `vpc-lattice:Invoke` is almost never in the NotAction list, the caller
  can invoke. Treat as INVOKE_ACCESS and apply Rule 5b.

- NEVER treat `aws:SourceIp` with `0.0.0.0/0` as a condition. This CIDR is
  the entire internet. Treat the statement as if the condition is absent.

- NEVER recommend removing the auth policy as remediation. Removing the auth
  policy returns the service network to NO_AUTH_POLICY (default-open), which
  is WORSE than a permissive policy. The remediation is to tighten the
  policy, not remove it.

- NEVER assume RAM sharing alone grants cross-account invocation. RAM
  sharing grants VISIBILITY (list, describe). Invocation requires the auth
  policy to Allow the consumer AND the consumer's IAM policy to include
  `vpc-lattice:Invoke`. However, without an auth policy, the RAM share +
  VPC association is sufficient — flag as NO_AUTH_POLICY.

- NEVER flag same-account `vpc-lattice:Invoke` with a STRONG condition
  (`aws:SourceVpc`, `aws:SourceAccount`) as CONFIG_GAP. Same-account access
  scoped by a strong condition is OK — the condition couples invocation to
  a known VPC or account that the caller controls.

- NEVER classify cross-account `vpc-lattice:Invoke` as OK, even when
  restricted by `aws:SourceAccount`, `aws:SourceArn`, or `aws:SourceVpc`.
  Cross-account invoke is ALWAYS at least CONFIG_GAP (Rule 5d). The STRONG
  condition narrows the blast radius but the external trust dependency
  remains — a compromised external account or policy edit widens exposure.
  Only same-account invoke with a STRONG condition is OK (Rule 5h). If the
  principal's 12-digit account ID differs from the service network's owning
  account, the finding is CONFIG_GAP regardless of conditions.

- NEVER treat IP target groups as equivalent to INSTANCE target groups.
  INSTANCE targets are bound to EC2 ENIs in the VPC (network-isolated).
  IP targets can point to ANY address — cross-VPC, cross-account, on-premises.
  An IP target outside the VPC CIDR is a CONFIG_GAP.

- NEVER assume the security group on the VPC association compensates for a
  missing auth policy. The security group controls network traffic to
  targets, not who can invoke services through Lattice. They are
  complementary layers, not substitutes.

- NEVER forget to archive backup auth-policy files after each change.
  `PutAuthPolicy` is atomic with no version history and no rollback API.
  Store the previous policy in a versioned location (S3 with versioning
  enabled, git, or a secrets manager) before every replacement. A lost
  backup means no recovery path — the only option is to reconstruct the
  policy from memory or CloudTrail management-event logs.

- NEVER assume `Resource: <specific-arn>` in a Lattice auth policy scopes
  the grant. The policy is attached to a service network or service; the
  Resource element is effectively ignored regardless of what you specify.
  Setting Resource to a single service ARN gives a false sense of scoping.
  Use Principal and Condition to restrict, not Resource.

- NEVER rely on `aws:SourceIp` conditions in a Lattice auth policy. Lattice
  proxies requests through its data plane, so the source IP is a Lattice
  internal address — not the original caller's IP. A SourceIp condition
  either matches unpredictably or blocks legitimate traffic. It is
  architecturally unreliable, not merely weak.

- NEVER skip IPv6 CIDR checks on target groups and security groups. Lattice
  supports IPv6; an IP target group with IPv6 targets (::/0, fc00::/7) is
  just as dangerous as IPv4 targets outside the VPC CIDR. Audit both
  families.

- NEVER ignore CloudWatch Lattice metrics during an audit window. A sudden
  spike in `ProcessedBytes` or `4xxErrorCount` for a service may indicate
  unauthorized invocation attempts. Correlate metrics with auth-policy
  findings to prioritize remediation.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`PutAuthPolicy`, `DeleteServiceNetwork`, `DeleteService`), the auditor
  MUST emit:
  `CONFIRM: About to <action> on service network <id> in account <account>.
  This affects <consequence>. Proceed? (yes/no)`
- **DeleteServiceNetwork is DESTRUCTIVE and NON-RECOVERABLE.** Deleting a
  service network severs ALL VPC associations and routing — every service
  in the network becomes unreachable instantly. There is no recycle bin.
  The auditor MUST require a second confirmation for DeleteServiceNetwork
  specifically, including a check that all associated VPCs and services
  have been enumerated and acknowledged. Prefer disassociating individual
  VPCs over deleting the network when scoping access.
- **PutAuthPolicy lockout prevention.** The replacement auth policy MUST
  include at least one Allow statement for a principal in the owning
  account. An auth policy that denies the owning account is an instant
  lockout — there is no version history and no rollback.
- Capture the current auth policy for rollback BEFORE any modification:
  `aws vpc-lattice get-auth-policy --resource-arn <arn> --output json >
  /tmp/<sn-id>-auth-policy-backup-$(date +%s).json`
- Before putting a new auth policy, verify ALL services in the network are
  still reachable by the intended callers. An overly restrictive policy
  silently breaks service-to-service communication.
- Prefer additive changes (add a Deny, add a condition) over destructive
  changes (remove an Allow) — additive changes are reversible.
- For NO_AUTH_POLICY findings, treat as high-priority — the service network
  is currently open. Remediate by attaching a scoped auth policy, not by
  disassociating VPCs (which breaks routing).

## Remediation guidance

### For NO_AUTH_POLICY — no auth policy (default-open)

1. Create a scoped auth policy:
   `aws vpc-lattice put-auth-policy --resource-arn <sn-arn> --policy
   file://auth-policy.json`

Sample scoped auth policy (NO_AUTH_POLICY remediation) — moved verbatim.
Full detail: [Worked examples](references/worked-examples.md).

### For PUBLIC_SERVICE_NETWORK — wildcard Invoke (Rule 5a/5b)

1. Replace `Principal: "*"` with specific same-account role ARNs.
2. Add `aws:SourceVpc` or `aws:SourceAccount` condition.
3. If `NotAction` is the source, replace with explicit `Action` allow-list.
4. Audit CloudTrail for `vpc-lattice:Invoke` events from unexpected principals
   during the exposure window.

### For CONFIG_GAP — cross-account invoke (Rule 5c/5d)

1. If cross-account access is NOT required, remove the external principal.
2. If cross-account IS required, add `aws:SourceAccount` and `aws:SourceArn`
   conditions to scope the grant.
3. Verify the consumer account's IAM policy also restricts Invoke to
   intended roles (intersection model).

### For CONFIG_GAP — IP target outside VPC CIDR (Step 6)

1. Verify the external IP is an intentional endpoint (on-premises via
   Direct Connect, cross-VPC via peering).
2. If unintentional, remove the target:
   `aws vpc-lattice deregister-targets --target-group-identifier <tg-id>
   --targets <target-list>`
3. If intentional, document the routing path and add a note to the finding.

### For CONFIG_GAP — RAM share without scoped policy (Step 7)

1. Verify the consumer account is expected.
2. Add the consumer account's role to the auth policy with conditions.
3. If the share is stale, remove it:
   `aws ram delete-resource-share --resource-share-arn <rs-arn>`

### For OK

1. No remediation required for the current posture.
2. Recommend periodically re-auditing service-level auth policies (they can
   be added independently and silently override the network policy).
3. Recommend adding a Deny on `aws:SecureTransport: false` for defense in
   depth.

## Expert knowledge: non-obvious VPC Lattice behaviors

Expert knowledge — non-obvious VPC Lattice behaviors — moved verbatim.
Full detail: [Advanced Patterns](references/advanced-patterns.md).

## Deep reference: Lattice authorization

Deep reference — Lattice authorization internals — moved verbatim.
Full detail: [Advanced Patterns](references/advanced-patterns.md).

## References (load on demand)

- [Worked examples](references/worked-examples.md) — secondary worked example (partially malformed policy), sample scoped auth policy
- [Error handling](references/error-handling.md) — malformed-policy ERROR output, live-audit API errors, CONFIG_GAP ticket rule
- [Diagnostic commands](references/diagnostic-commands.md) — live-account pre-flight checks (services, RAM shares, IAM intersection, pagination, consistency)
- [Advanced patterns](references/advanced-patterns.md) — edge-case catalog, Step-1/Rule-5d rationale, expert knowledge, deep authorization reference

## Domain

AWS CloudOps / VPC Lattice Application Networking Security.

## AWS documentation

- **VPC Lattice User Guide** — https://docs.aws.amazon.com/vpc-lattice/latest/ug/
- **VPC Lattice Security** — https://docs.aws.amazon.com/vpc-lattice/latest/ug/security.html
- **Auth policies** — https://docs.aws.amazon.com/vpc-lattice/latest/ug/auth-policies.html
- **VPC Lattice API Reference** — https://docs.aws.amazon.com/vpc-lattice/latest/APIReference/
- **AWS CLI Command Reference (VPC Lattice)** — https://docs.aws.amazon.com/cli/latest/reference/vpc-lattice/
- **Cross-account sharing with RAM** — https://docs.aws.amazon.com/vpc-lattice/latest/ug/sharing.html
