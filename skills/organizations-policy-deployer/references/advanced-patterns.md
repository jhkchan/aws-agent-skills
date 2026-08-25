# Advanced Patterns — Organizations Policy Deployer

Deep-dive material moved out of the SKILL.md body so the procedure
stays scannable. Loaded on demand by the skill.

## Mindset

**One-line takeaway:** An SCP is a permission boundary — it can
only RESTRICT what IAM allows; it can never GRANT. Every account
in an organization gets `FullAWSAccess` attached by default, and
removing it without an explicit Allow-list replacement locks the
account out. SCP inheritance is an INTERSECTION: the effective
SCP at any account is the intersection of all SCPs attached to
the root, every parent OU, and the account itself. The most
restrictive SCP always wins; an explicit Deny anywhere in the
hierarchy overrides every Allow.

Four misconceptions dominate SCP misdesign at deployment time:

- **"An SCP grants permissions."** It does NOT. An SCP is a
  permission boundary that filters what IAM can do. An IAM
  principal can call an API only if BOTH the IAM policy ALLOWS it
  AND no SCP in the hierarchy DENIES it.

- **"Removing FullAWSAccess is enough to lock down an account."**
  Removing `FullAWSAccess` WITHOUT attaching a replacement
  Allow-list SCP leaves the account in a deny-by-default state
  where member-account IAM principals cannot call ANY AWS API —
  including break-glass. Always attach an Allow-list SCP first.

- **"SCP inheritance unions — the broadest SCP wins."** It does
  NOT. Inheritance is an INTERSECTION. If the root SCP allows
  `ec2:*` and a child OU SCP restricts to `ec2:Describe*`, the
  child OU wins — only `ec2:Describe*` survives.

- **"SCPs are IAM policies."** They are NOT IAM. SCPs live in
  Organizations, apply to the whole account (including root), and
  CANNOT grant anything. A `Resource: "*"` Allow in an SCP means
  "passes the SCP filter"; it does NOT mean the principal can
  call the API. (See Step 1 for the comparison table.)

## Configuration dependency graph (novel heuristic)

Organizations policy deployment is NOT a single attach call. The
policy must be created before it can be attached;
`FullAWSAccess` must remain attached (or be replaced by an
Allow-list SCP) or the account locks out; tag and backup policies
are separate policy types with their own enablement; AI services
opt-out is organization-wide and one-shot.

| Configuration | Hard dependencies (API error without) | Silent failure | Enables downstream |
|---|---|---|---|
| SCP creation (create-policy) | "All features" org; organizations:CreatePolicy | SCP created ENABLED but inert until attached | policy available to attach |
| SCP attachment (attach-policy) | target exists; policy ENABLED | root attachment affects EVERY account (incl. break-glass) | policy takes effect |
| FullAWSAccess | AWS-managed, attached by default | detaching WITHOUT a replacement Allow-list locks the account out | baseline Allow |
| Allow-list strategy SCP | child SCP listing ONLY permitted services | if FullAWSAccess remains attached, Allow-list is redundant | least-privilege boundary |
| Deny-list strategy SCP | child SCP with explicit Denies | explicit Deny wins regardless of other Allows | guardrail |
| Tag policy (TAG_POLICIES) | `enable-policy-type --policy-type TAG_POLICIES` | non-blocking by default; add `enforced_for` to make it blocking | tag standardization |
| Backup policy (BACKUP_POLICY) | `enable-policy-type --policy-type BACKUP_POLICIES` | applies to supported resource types only; tag-based selection | org-level backup plan |
| AI services opt-out (AISERVICES_OPT_OUT_POLICY) | org "All features" | ALL-OR-NOTHING per service across ALL accounts — no per-account opt-in | data-usage governance |
| Delegated administrator | account is a member account | delegated admin gets read/list only — CANNOT create/attach SCPs | cross-account read administration |

**The FullAWSAccess-removal row is the one a baseline model
misses.** An Allow-list SCP has zero effect while
`FullAWSAccess` is still attached at the same entity, because
the intersection still permits everything `FullAWSAccess`
permits. The procedure below forces an explicit decision on
whether to keep or remove `FullAWSAccess` at each entity.

## Step 15 — Recent features


**Recent AWS features (2023-2026):**

- **Effective-SCP visualization (2023-2024):** Organizations
  console renders the effective-SCP intersection at every
  account. Scriptable via `list-policies-for-target` +
  `list-parents`.
- **Backup policy support for Aurora, FSx, stacked resources
  (2023-2024):** Tag-based selection matches
  `aws:ResourceTag/*` with `StringLike` for prefix matching.
- **AI services opt-out expansion (2023-2025):** New AI services
  auto-fall-under the `default` key when
  `opt_out_enabled_at_level: account` is set.
- **Tag policy enforcement for EC2 network interfaces and EBS
  snapshots (2024-2025):** `enforced_for` accepts
  `ec2:network-interface` and `ec2:snapshot`.
- **CloudTrail `organizations:EffectiveApiName` (2024-2025):**
  Deny events now include the SCP statement Sid that triggered
  the Deny.
- **Delegated administrator expansion (2024-2025):** New
  delegable principals (Audit Manager, Resource Explorer 2,
  Systems Manager QuickSetup). Each is service-scoped — none
  grant SCP-write.

