# Advanced Patterns — shield-advanced-coverage-auditor

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

---

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across
all dimensions, ordered UNPROTECTED > NO_DRT_ACCESS > CONFIG_GAP > OK — and
two resources (CloudFront, Route 53) are **auto-protected** by Shield
Advanced, so flagging their absence from the Protections list is the most
common false positive.

Shield Advanced is the paid tier of AWS Shield (Standard is free, L3/L4
only). The coverage audit answers one question: **is every internet-facing
resource in this account getting the full Shield Advanced value?** Three
dimensions define "full value":

- **Coverage** — every ALB/NLB/CLB and EIP-backed EC2 instance has an
  explicit Protection (CloudFront and Route 53 are auto-protected).
- **DRT access** — the DDoS Response Team can assume a role AND read access
  logs to create targeted WAF mitigations during an attack.
- **Detection + engagement** — health-based detection is wired so Shield
  sees L7 application-layer attacks, and proactive engagement is enabled so
  the DRT calls you before you call them.

A resource with Shield Standard only is behind the first line of defence but
NOT behind Shield Advanced's enhanced detection, DRT manual mitigation, or
cost-protection credits. That gap is what this auditor catches.


### Step 0: Expert knowledge — non-obvious behaviors that change classification

These behaviors cause false positives or silent failures if ignored. Each
is explained in depth in [Deep reference: Shield Advanced
internals](#deep-reference-shield-advanced-internals); the one-liner here
is the classification-impacting summary.

- **CloudFront + Route 53 are AUTO-PROTECTED** (re:Invent 2023). Flagging
  their absence from the Protections list is the #1 false positive.
- **DRT needs BOTH a role AND log-bucket access.** No role = NO_DRT_ACCESS.
  Role but no log bucket = CONFIG_GAP (blind, not helpless).
- **Proactive engagement needs EnableProactiveEngagement AND a populated
  EmergencyContactList.** ENABLED with empty contacts = CONFIG_GAP.
- **Health-based detection is PER-PROTECTION.** Missing = CONFIG_GAP and
  disqualifies cost-protection credits.
- **WAF Web ACL is required for L7 mitigation.** ALB Protection without
  WAF = CONFIG_GAP (L3/L4 only).
- **Application Layer Automatic Response** (2023 GA) auto-tunes WAF rules
  without DRT — verify it on critical ALBs (requires WAF Web ACL).
- **`ListProtections` caps at 100/page** — paginate with `NextToken` or
  silently miss Protections on page 2+.
- **Match on `ResourceArn`, never `Name`** — Name is not unique; ARN is.
- **DRT role trust policy needs `service-role.shield.amazonaws.com`** —
  `shield.amazonaws.com` fails silently at incident time.
- **`AssociateHealthCheck` is write-only** — verify associations via
  `DescribeProtection`, not `route53 list-health-checks`.
- **EIP Protection uses allocation ID** (`eipalloc-xxx`), not public IP.
- **Subscription auto-renews** — 1-year term, non-prorated, silent renewal.


## Edge-case handling

- **Partially populated Protections list.** If the Protections list has
  some but not all ALBs, classify each missing ALB as UNPROTECTED and each
  present ALB as OK. Do NOT classify the entire account as UNPROTECTED if
  only one ALB is missing — enumerate per-resource findings so the operator
  can prioritize.

- **EC2 instance without EIP.** An EC2 instance with only a private IP
  cannot be DDoS-attacked from the internet. Do NOT flag it as UNPROTECTED.
  Only EC2 instances with an associated EIP (public IP) are in scope.

- **Resource re-created with a new ARN.** If an ALB was deleted and
  re-created (e.g., via Terraform destroy/apply), its ARN changed. The old
  Protection still references the old ARN and is now a stale entry. The
  new ALB is UNPROTECTED. Flag the stale Protection AND the missing
  coverage. Remediation: delete the stale Protection, create a new one
  for the new ARN.

- **Global Accelerator.** Global Accelerator is protected by Shield
  Advanced at the accelerator level. An accelerator without explicit
  Protection is UNPROTECTED. Treat like ALB — check the Protections list
  for the accelerator ARN.

- **CloudFront distribution in a different account.** Shield Advanced
  auto-protection applies per-account. A CloudFront distribution in account
  A is auto-protected by account A's Shield Advanced subscription, NOT by
  account B's. If auditing across accounts (Organizations), verify each
  account has an active subscription.

- **DRT role deleted outside Shield.** If the IAM role referenced by
  `AssociateDRTRole` was deleted directly in IAM (not via Shield), the DRT
  access state is stale — `DescribeDRTAccess` may still return the old
  RoleArn. The DRT cannot assume a deleted role. Treat as NO_DRT_ACCESS
  and re-associate a valid role.

- **Empty Protections list with only CloudFront/Route 53.** If the only
  internet-facing resources are CloudFront distributions and Route 53
  hosted zones, the Protections list can be legitimately empty (both are
  auto-protected). Do NOT flag an empty Protections list as UNPROTECTED if
  no ALB/NLB/CLB/EIP resources exist.


## Deep reference: Shield Advanced internals

### Coverage model — auto vs explicit

Shield Advanced protection operates in two modes:

1. **Auto-protection (CloudFront, Route 53):** Once subscribed, ALL
   distributions and hosted zones are protected automatically. The
   `ListProtections` API does NOT list these — they are implicit. There is
   no `CreateProtection` call for these resource types; the API rejects it.

2. **Explicit protection (ALB, NLB, CLB, EIP, Global Accelerator):** Each
   resource must be individually added via `CreateProtection`. The
   `ListProtections` API returns these. Coverage gaps occur when resources
   are created without adding a Protection.

### Non-obvious classification gotchas — detailed

The one-liners in Step 0 summarize these; the full operational detail is
here for agents that need the reasoning behind each classification call.

- **DRT role trust policy principal.** The IAM role passed to
  `AssociateDRTRole` must have a trust policy allowing
  `service-role.shield.amazonaws.com` — not `shield.amazonaws.com`. The
  Shield API does NOT validate the trust policy on association; it
  accepts the role ARN silently. The failure surfaces only when the DRT
  attempts `sts:AssumeRole` during a live attack and receives
  `AccessDenied`. This is a silent NO_DRT_ACCESS that
  `DescribeDRTAccess` reports as healthy (it returns the RoleArn).

- **`AssociateHealthCheck` is write-only.** There is no Shield API to
  list which health checks are associated with which Protections. You
  MUST call `DescribeProtection` per Protection and read
  `HealthCheckIds`. `route53 list-health-checks` lists all health checks
  but does not indicate Shield associations. An auditor that assumes
  "a health check exists in Route 53, therefore the protection is
  covered" will produce false OK verdicts.

- **EIP Protection uses the allocation ID.** The `ResourceArn` for an EIP
  is `arn:aws:ec2:<region>:<account>:elastic-ip/eipalloc-xxx`. Using the
  public IP or EC2 instance ARN fails silently — `CreateProtection`
  accepts the string but the protection references a non-existent
  resource. The DRT cannot mitigate a resource that doesn't resolve.
  Verify via `aws ec2 describe-addresses` before creating.

- **Cost-protection credits require health checks AND WAF.** Without
  health-based detection, Shield cannot demonstrate to the cost-protection
  team that the scaling was caused by a detected DDoS event. Without WAF
  on an L7 attack, there is no mitigation record. Both are gating
  conditions for credit approval — their absence is a financial risk,
  not just a detection gap.

- **Subscription auto-renewal trap.** `CreateSubscription` starts a
  1-year term that auto-renews unless explicitly cancelled before the
  renewal date. There is no proration. An account subscribed for a
  one-time event (product launch, election night) that forgets to cancel
  will be billed silently for year 2. The confirmation gate must surface
  this.

- **`DescribeDRTAccess` can return a stale RoleArn.** If the IAM role
  referenced by `AssociateDRTRole` was deleted directly in IAM (not via
  `DisassociateDRTRole`), the Shield API may still return the old
  RoleArn. The DRT cannot assume a deleted role. This is a silent
  NO_DRT_ACCESS — cross-reference the RoleArn against live IAM roles
  using `iam get-role`.

- **TAG-based Protection grouping is not coverage.** Shield Advanced has
  no native resource-group or tag-based protection. Each Protection is a
  1:1 mapping to a single `ResourceArn`. An operator who assumes "all
  resources tagged `shield=protected` are covered" will miss any
  resource without an explicit Protection entry. Do not infer coverage
  from tags.

### DRT incident-response workflow

During a suspected DDoS event:
1. Shield Advanced always-on detections trigger (L3/L4 volumetric).
2. If health-based detection is configured, L7 degradation also triggers.
3. The DRT is notified automatically.
4. If proactive engagement is ENABLED, the DRT calls the emergency contacts.
5. The DRT assumes the associated IAM role and creates WAF rate-based rules
   in the resource's Web ACL.
6. If no DRT role is associated, the DRT cannot act — you must self-mitigate.
7. If no log bucket is associated, the DRT operates blind to log-level
   attack patterns.

### Cost-protection eligibility

Shield Advanced credits the cost of auto-scaling triggered by a DDoS
attack, subject to:
- The affected resource must have an active Protection.
- Health-based detection must be configured (Route 53 health check
  associated).
- For L7 attacks, a WAF Web ACL must be associated.
- The attack must be confirmed by AWS as a DDoS event.

Without health checks and WAF, cost-protection credits may be denied.

### Subscription lifecycle

- `CreateSubscription` starts a 1-year term. The monthly fee is charged
  from day one.
- The subscription auto-renews at the end of the term unless cancelled.
- There is no proration — cancelling mid-term does not refund remaining
  months.
- `DeleteSubscription` is available but does not refund. Protections,
  DRT access, and health-check associations persist but become
  non-functional (Shield Standard takes over).


## Recent AWS features (2024-2026)

- **Automatic application layer DDoS mitigation (2023 GA, 2024 enhanced):**
  Shield Advanced can now automatically create and tune WAF rules per-protection
  without DRT manual intervention, via
  `EnableApplicationLayerAutomaticResponse`. Auditors should verify that
  critical ALB protections have automatic response enabled — it reduces
  response time for known L7 attack patterns from minutes to seconds.
  Note: this requires a WAF Web ACL to be associated with the protection.

- **CloudFront and Route 53 automatic protection (re:Invent 2023):**
  All CloudFront distributions and Route 53 hosted zones are now
  auto-protected by Shield Advanced at no additional per-resource cost.
  Auditors must NOT flag these resources as UNPROTECTED for absence from
  the Protections list — this is the most common false positive.

- **Enhanced DRT visibility (2024-2025):** The DRT console now provides
  real-time attack visibility and mitigation tracking. Auditors should
  verify that the DRT has both role and log-bucket access to take full
  advantage of enhanced visibility features.

- **Shield Advanced health-check integration improvements (2024):**
  Improved correlation between Route 53 health checks and Shield Advanced
  detections, reducing false-negative L7 detection. Auditors should verify
  health checks are associated with all critical explicit protections.

- **Proactive engagement workflow updates (2024-2025):** Enhanced
  notification routing and multi-contact support. Auditors should verify
  the emergency contact list is current — stale contacts defeat proactive
  engagement.

