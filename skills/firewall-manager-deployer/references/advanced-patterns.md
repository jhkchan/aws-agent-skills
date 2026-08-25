# Advanced Patterns — Firewall Manager Deployer

Expert-heuristic deep dives and recent-feature notes, moved verbatim from SKILL.md. Load on demand.

## Expert heuristic: policy priority evaluation order (first-match wins)
A baseline model says "create the policy." The correct heuristic
recognizes that when multiple policies of the same type target
overlapping resources, FMS evaluates in priority order — first match
wins, and lower-priority policies are NOT applied to those resources.

```text
Policy Type: WAF
  Policy A (priority 1): OU=Prod, RuleGroup=AWSManagedRulesCommonRuleSet
  Policy B (priority 2): OU=Root (all accounts), RuleGroup=CustomRules

Account 111111111111 is in OU=Prod:
  → Evaluated by Policy A (priority 1, first match)
  → Gets AWSManagedRulesCommonRuleSet
  → Policy B does NOT apply (already covered by Policy A)

Account 222222222222 is NOT in OU=Prod:
  → Policy A does not match (OU scope excludes it)
  → Evaluated by Policy B (priority 2, next match)
  → Gets CustomRules

Key: if you want Policy B to also apply to Prod accounts, use a
different policy type, or restructure so Policy A and B target
non-overlapping resource sets.
```

**Key implication:** policy priority ordering is critical for layered
designs. Always verify which policy is the first match for each target
account.

## Expert heuristic: OU scope vs account scope expansion
FMS policies can target an entire Organization, specific OUs, or
individual accounts. OU-based targeting automatically expands to include
all accounts currently in the OU AND accounts moved into the OU later.

```text
Targeting options (broadest to narrowest):
  ├── Organization → all accounts in the Organization (including future)
  ├── OU → all accounts in the OU (including future additions)
  ├── OU + sub-OUs → all accounts in the OU and its children
  └── Individual accounts → only the listed accounts (no auto-expansion)

OU expansion behavior:
  OU=Workloads
    ├── Prod (accounts: 111, 222, 333)
    │     └── New account 444 added later → automatically in scope
    └── Dev (accounts: 555, 666)

Exclude mechanism: add ExcludeAccounts or ExcludeResourceTags to
override OU scope for specific accounts or tagged resources.
```

**Key implication:** OU-based targeting is dynamic. New accounts moved
into the OU are automatically in scope. Use exclude tags for resources
that must opt out of a policy.

## Expert heuristic: remediation grace period
Remediation mode determines whether FMS actively fixes noncompliant
resources or just reports them. The grace period adds a delay before
auto-remediation.

```text
Remediation modes:
  RemediationEnabled=false (monitor-only):
    → Noncompliant resources reported in FMS console + Config
    → NO automatic changes to resources
    → Use for phased rollout / auditing

  RemediationEnabled=true (auto-apply):
    → FMS automatically creates/modifies resources to comply
    → Grace period (days) delays remediation after detection
    → RemediationGracePeriodDays: 0 = immediate, 7 = 1 week buffer

Grace period decision framework:
  ├── New policy, first rollout → monitor-only for 1-2 weeks
  ├── Confident, ready to enforce → auto-apply with 7-day grace
  ├── Mature, strict enforcement → auto-apply with 0-day grace
  └── Critical production, no tolerance → auto-apply with 0-day grace
```

**Key implication:** always start with monitor-only for new policies,
then transition to auto-apply with a grace period once the compliance
posture is understood.

## Step 12 — Recent features
**Recent AWS features (2023-2026):**

- **FMS WAFv2 policy support (2023-2024):** Full support for WAFv2
  managed rule groups in FMS policies, including version-pinned rule
  groups and managed rule group marketplace integrations.

- **FMS Network Firewall policy enhancements (2023-2024):** Improved
  subnet mapping automation and stateful rule group support in Network
  Firewall policies. Policies can now auto-create firewall subnets in
  target accounts.

- **FMS Shield Advanced auto-remediation (2023-2024):** Shield Advanced
  policies now automatically apply proactive DDoS mitigations and
  layer 7 rate-based rules without manual Shield engagement.

- **FMS DNS Firewall policy support (2023-2024):** Route 53 Resolver
  DNS Firewall policies can now be managed via FMS, enabling
  centralized DNS threat protection across the Organization.

- **FMS third-party managed rule groups (2024-2025):** Marketplace rule
  groups (e.g., Imperva, F5, Imperva) can now be referenced in FMS WAF
  policies, expanding the managed rule ecosystem.

- **FMS policy priority reordering (2024-2025):** Enhanced priority
  management allowing dynamic reordering without recreating policies,
  making layered security designs easier to maintain.

- **FMS compliance notifications via Security Hub (2024-2025):** FMS
  compliance findings now automatically integrate with Security Hub,
  providing a unified security posture view across WAF, SG, Network
  Firewall, and Shield Advanced policies.
