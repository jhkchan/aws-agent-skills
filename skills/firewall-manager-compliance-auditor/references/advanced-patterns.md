# Advanced Patterns — Firewall Manager Compliance Auditor

Expert-knowledge deep dives, edge-case catalogs, and reference material, moved verbatim from SKILL.md. Load on demand.

## When to invoke
**Invoke pattern:** the operator provides an FMS policy JSON (from
`aws fms get-policy` or `list-policies`) AND asks about compliance,
scope, or enforcement posture. Specifically, invoke when the operator
asks any of:

- "audit this FMS policy" / "check FMS compliance" / "is this FMS
  policy enforced?"
- "FMS coverage gap" / "is my FMS scope correct?"
- "why does FMS report zero violations?" (the Config-disabled dark-spot
  trap)
- "is the FMS policy NOT_READY?" / "PolicyState NOT_READY"
- "is RemediationEnabled off?" / "FMS detect-only mode"
- "does this Shield Advanced FMS policy cover all resources?"
- "is this a legacy WAF Classic FMS policy?" / "PolicyType WAF"
- "FMS IncludeMap / ExcludeMap coverage"
- "audit my FMS deployment" / "audit firewall manager"
- reviewing an FMS policy before a compliance review, production
  rollout, or org-wide deployment

Do NOT invoke for: per-WebACL rule analysis (use
`wafv2-web-acl-auditor`), per-SG rule analysis (use
`ec2-security-group-auditor`), or Shield Advanced resource-level
protection audits outside FMS (use `shield-advanced-coverage-auditor`).
This skill audits the FMS policy layer — how WAF/SG/Shield/Network
Firewall are applied and enforced across accounts — not the underlying
rule sets.

### Step 0: Expert knowledge — non-obvious FMS behaviors
Each behavior below changes a verdict if ignored. Detailed mechanics
for PolicyState, RemediationEnabled, ResourceTags scope, and
PolicyType currency are in Steps 1–7 — this section covers what the
Steps do not.

- **`EvaluationLimitExceeded` produces a silent false-compliant.** In
  `list-compliance-status`, each `PolicyComplianceStatus` can carry
  `EvaluationLimitExceeded: true`. When Config cannot complete
  evaluation for a member (resource explosion, throttling), FMS marks
  the member compliant by default — not unknown. A `true` value
  invalidates the compliance verdict for that account.

- **Cost trap: stale FMS policies generate continuous Config charges.**
  Each policy triggers AWS Config evaluations per-resource per-region
  per-cycle. One policy scoped to `AwsEc2Instance` across 500 accounts
  = ~500 evaluations per region per cycle. Unused policies (>90 days,
  ProtectedResourceCount=0) are a measurable cost leak in Cost Explorer
  under `AWS Config`.

- **FMS remediation in CloudTrail shows the service-linked role.** When
  FMS auto-applies a WebACL (`wafv2:AssociateWebACL`), the CloudTrail
  actor is `AWSServiceRoleForFMSService`, not the operator. Correlate
  with `fms:PutPolicy` events by timestamp for incident attribution.

- **`PutPolicy` with `ResourceType: ""` (empty string) is accepted but
  matches zero resources.** The API does not reject it. Always validate
  `ResourceType` is non-empty before `put-policy`.

- **ResourceTags multi-value semantics: AND across keys, OR within
  values.** `[{Key:env,Value:prod},{Key:tier,Value:web}]` = env=prod
  AND tier=web. Multi-value tags narrow scope — flag if the intent
  was OR.

- **ExcludeMap wins over IncludeMap** (mirrors IAM explicit-deny). An
  account in both is excluded. Always cross-reference both maps — an
  ExcludeMap entry silently punches holes in coverage.

- **FMS uses AWS Config as its sole compliance data source.** A member
  with Config disabled is a dark spot: `NonCompliantResourceCount`
  reads 0 (no data), not "compliant." Cross-reference Config recorder
  status before trusting any clean count.

- **`PutPolicy` is atomic per policy, not per resource.** A WebACL swap
  applies to ALL in-scope resources simultaneously — no staged rollout.
  Edit the WebACL via `wafv2` for reversible changes.

- **PolicyType-specific resource vocabularies.** Each PolicyType
  accepts a constrained set; entries outside the allowed set are
  silently ignored. Key types: WAFV2 → `AwsWafv2WebAcl`,
  `AwsApiGatewayStage`, `AwsElasticLoadBalancingV2LoadBalancer`,
  `CloudFrontDistribution`; SHIELD_ADVANCED → `AwsEc2Eip`,
  `AwsElasticLoadBalancingV2LoadBalancer`, `CloudFrontDistribution`;
  SECURITY_GROUPS_* → `AwsEc2Instance`, `AwsEc2NetworkInterface`;
  NETWORK_FIREWALL / DNS_FIREWALL → `AwsEc2Vpc`.

- **Quota: 50 FMS policies per org** (soft cap). `put-policy` at the
  cap fails with `LimitExceededException`.

## Edge-case handling
- **Partially malformed policy.** If the policy JSON parses but
  individual fields are missing (`PolicyType`, `PolicyId`), classify
  the valid dimensions and emit an ERROR note for each malformed field.
  Do NOT silently classify the entire policy as ERROR when only one
  field is broken.

- **Multi-policy aggregation.** When auditing an entire FMS deployment
  (`aws fms list-policies`), classify each policy independently. The
  deployment-level verdict is the worst across all policies. A single
  NONCOMPLIANT policy makes the deployment NONCOMPLIANT.

- **Cross-admin-scope policies.** With multiple FMS administrators
  (per-OU delegation, available 2024+), each admin sees only its scope.
  `list-policies` returns only policies the calling admin manages. A
  "clean" deployment from one admin's perspective may have policies
  owned by another admin — cross-reference `get-admin-scope` to map
  coverage.

- **ResourceTags with multiple values.** FMS treats multi-value
  ResourceTags as logical AND across keys, OR within values
  (`[{Key: env, Value: prod}, {Key: tier, Value: web}]` = env=prod AND
  tier=web). Multi-value tags narrow scope — flag if the intent was OR.

- **Policy with `DeleteUnusedFMSPolicies: true`.** This is a hygiene
  flag, not a security verdict driver. Note it as OK with a comment
  "auto-cleanup enabled."

- **Stale `IncludeMap` OUs.** An OU that has been dissolved (deleted
  from Organizations) but remains in `IncludeMap` is silently ignored
  by FMS. The policy applies to fewer accounts than the operator
  believes. Cross-reference `aws organizations list-ous` and flag stale
  entries as CONFIG_GAP.

- **Empty ResourceTypeLists AND non-empty ResourceType (singular).**
  Treat the singular `ResourceType` as the effective scope. Do NOT flag
  as empty — the field is the legacy form.

## Advanced execution topics (FMS quotas, ExcludeMap precedence, enforcement pipeline, AWS Config coupling, region semantics, PolicyType migration paths)
### FMS quotas (the quantitative guardrails)

- **50 FMS policies per organization** (soft cap). Remediations that
  propose new policies must validate headroom via `aws fms list-policies
  | jq 'length'` before `put-policy`. Hitting the cap mid-remediation
  leaves the org in a partially-migrated state.
- **1 FMS administrator account per org** (legacy) or multiple admins
  per OU scope (2024+). With multiple admins, each admin's
  `list-policies` is scoped — enumerate all admins via
  `aws fms list-admin-accounts-for-organization` to get the full policy
  set.
- **AWS Config recorder must be enabled** in every member account in
  every in-scope region. A member with Config disabled is a dark spot
  — `NonCompliantResourceCount` reads 0 (no data), not "compliant".
- **FMS service-linked role (`AWSServiceRoleForFMSService`)** must
  exist in every member account. FMS auto-creates it on first policy
  application; if a member deleted it, enforcement silently fails and
  the resource stays NONCOMPLIANT. Verify via
  `aws iam get-role --role-name AWSServiceRoleForFMSService` per member.
  Recovery: `aws iam create-service-linked-role --aws-service-name
  fms.amazonaws.com`.

### ExcludeMap precedence and stale-OU handling

- **Exclude wins over Include.** An account appearing in both
  `IncludeMap` and `ExcludeMap` is EXCLUDED. This mirrors IAM
  evaluation (explicit deny wins). Always cross-reference both maps —
  an ExcludeMap entry silently punches holes in coverage.
- **Stale OU IDs** in `IncludeMap` are silently ignored by FMS (the OU
  was dissolved or recreated). Cross-reference
  `aws organizations list-roots` recursively and flag any
  `IncludeMap.ORG_UNIT` entry not in the current tree as a CONFIG_GAP.
- **Account-level IncludeMap entries** do not auto-track new accounts
  joining an OU. Use OU-level scoping whenever possible — it auto-tracks
  org changes.
- **Shield Advanced CloudFront scope** is global; `IncludeMap.ACCOUNT`
  still applies (the resource owner account). Verify CloudFront
  distributions in excluded accounts are intentionally unprotected.



### Enforcement pipeline

When FMS enforces a policy on a member account, the sequence is:

1. **AWS Config** discovers resources in the member account and
   evaluates them against the FMS policy's scope (ResourceTypeLists ×
   ResourceTags × IncludeMap).
2. **FMS service-linked role** in the member account
   (`AWSServiceRoleForFMSService`) is assumed by FMS to apply the
   WebACL/SG/Shield protection. If the role is missing or modified,
   enforcement silently fails.
3. **Resource tagging check** — resources must match ResourceTags if
   specified. Resources without the tag are excluded from scope
   entirely.
4. **WebACL/SG application** — FMS calls `wafv2 associate-web-acl` /
   `ec2 modify-network-interface-attribute` / `shield create-protection`
   on each in-scope resource.
5. **Compliance reporting** — FMS writes `PolicyComplianceStatus` per
   member account, observable via `list-compliance-status`.

A break at any stage produces NONCOMPLIANT resources. The stage of
breakage is NOT reported — operators must drill via
`get-compliance-detail` to identify root cause.

### AWS Config coupling

FMS is structurally dependent on AWS Config:
- Config discovers resources; FMS uses Config's resource inventory as
  its source of truth.
- Config's `ConformancePack` and `ConfigRule` are separate from FMS —
  FMS has its own compliance dimension.
- A member account with Config disabled is a dark spot: FMS sees zero
  resources, zero violations. The absence of data is NOT the absence of
  exposure.
- Config recorder coverage gaps (e.g., recorder not recording EC2)
  produce partial FMS visibility — `NonCompliantResourceCount` may
  undercount.

### Region semantics

- WAF, SG, and Network Firewall policies are **regional** — a policy
  in us-east-1 protects resources in us-east-1 only.
- Shield Advanced CloudFront protection is **global** — CloudFront
  distributions are global resources; the policy applies regardless of
  region.
- Shield Advanced EIP/ALB/NLB/CLB protection is **regional**.
- A multi-region workload requires auditing N regional FMS policies.
  Use `aws fms list-policies --region <r>` per region.

### PolicyType migration paths

- **WAF Classic → WAFv2**: create a new WAFV2 FMS policy with an
  equivalent WAFv2 WebACL. Verify `ProtectedResourceCounter` parity.
  Then delete the legacy WAF policy. There is no in-place migration —
  the PolicyType is immutable per policy.
- **SG COMMON → CONTENT_AUDIT**: these are distinct policy types with
  distinct purposes. COMMON applies a baseline; CONTENT_AUDIT audits
  existing SG rules. Both can coexist on the same resource scope.

## Condition strength reference (FMS-specific)
| Condition | Strength | Reason |
|---|---|---|
| ResourceTags + SCP tag enforcement | STRONG | SCP requires the tag on resource creation; FMS scope tracks the tag. Coupled, they prevent bypass. |
| ResourceTags only | WEAK | Tags are mutable; operators can remove them to escape FMS scope. Without SCP enforcement, the boundary is advisory. |
| IncludeMap `ORG_UNIT` | STRONG | Org tree is the source of truth; OU membership is enforced by Organizations. |
| IncludeMap `ACCOUNT` | MODERATE | Account IDs are stable but specific — easy to miss new accounts joining the org. |
| ExcludeMap | STRONG | Exclude wins. An ExcludeMap entry is a deliberate carve-out. |
| ResourceTypeLists | STRONG | Resource type is intrinsic to the resource; not bypassable. |

## Recent AWS features (2024-2026)
- **Network Firewall stateless rules (2024):** FMS manages stateless
  Suricata rule groups. Verify `FirewallPolicy` includes both stateful
  and stateless — stateless-only is a coverage gap.
- **DNS Firewall GA (2024):** FMS manages Route 53 Resolver DNS
  Firewall rule groups per-VPC. Verify VPC associations exist — FMS
  manages the rule group, not the association.
- **Third-party / Imported firewall (2024-2025):** Fortinet FortiGate
  Cloud, Palo Alto Cloud NGFW, and imported policies. Verify vendor
  registration via `list-third-party-firewall-firewall-policies`.
- **Per-OU admin delegation (2024-2025):** Multiple FMS admins manage
  distinct OU scopes. Enumerate all admins via
  `list-admin-accounts-for-organization` — one admin's view does not
  imply org-wide coverage.
- **DefaultApplicationReportingCriteria (2024-2025):** FMS reports on
  apps outside explicit policy scope when enabled. Check `GetAdminScope`
  response.
