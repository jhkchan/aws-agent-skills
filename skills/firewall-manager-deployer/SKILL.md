---
name: firewall-manager-deployer
description: 'Provisions AWS Firewall Manager (FMS) policies with production defaults: policy creation (WAF, Security Group, Network Firewall, Shield Advanced), managed service administrator account setup, AWS Organizations integration (OU-based targeting), remediation mode (auto-apply vs monitor-only), resource tagging for inclusion and exclusion, WAF managed rule group association, security group policies (common vs content audit), Network Firewall policy deployment, compliance status via AWS Config, resource group scoped policies, cross-account and cross-Region resource scope, and policy priority ordering. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating an FMS policy, managing firewall rules across an AWS Organization, setting up WAF managed. Triggers: create fms policy, firewall manager policy, fms waf policy, fms security group policy, fms network firewall policy, fms shield advanced, fms remediation, fms managed rule groups, fms ou targeting, fms policy priority, fms resource tags.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with fms, wafv2, ec2, network-firewall, shield, organizations, and config access. Requires the FMS administrator account to be delegated in AWS Organizations. Works with Terraform aws_fms_policy / aws_fms_admin_account resources and CloudFormation AWS::FMS::Policy templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, firewall-manager, fms, cloudops, deploy, security, provisioning, organizations, remediation, compliance
  dependencies: aws-orchestrator
  keywords: aws, firewall manager, fms, waf, security group, network firewall, shield advanced, cloudops, deploy, provisioning, organizations, remediation, managed rule groups, policy priority, compliance
  when_to_use: Invoke when the user wants to create an AWS Firewall Manager policy (WAF, Security Group, Network Firewall, or Shield Advanced), set up the FMS administrator account, target an Organization OU, configure remediation (auto-apply or monitor-only), manage WAF managed rule groups centrally, enforce security group policies across accounts, deploy Network Firewall policies at scale, or configure resource inclusion/exclusion via tags. Do NOT invoke for standalone WAFv2 Web ACL deployment (use wafv2-web-acl-deployer), standalone Network Firewall rule deployment (use network-firewall skills), or Shield Advanced configuration without FMS orchestration.
---

# Firewall Manager Deployer

An AWS CloudOps agent skill that provisions AWS Firewall Manager (FMS)
policies with correct defaults. The skill walks the operator through
policy type selection (WAF, Security Group, Network Firewall, Shield
Advanced), administrator account delegation, AWS Organizations
integration with OU-based targeting, remediation mode decisions, WAF
managed rule group association, security group policy modes (common vs
content audit), resource tag inclusion/exclusion, policy priority
ordering, and compliance monitoring via AWS Config, captures topology
and enforcement decisions, explains why each default matters, and emits
a READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## Activation keywords

create FMS policy, firewall manager policy, FMS WAF policy, FMS security
group policy, FMS Network Firewall policy, FMS Shield Advanced, FMS
remediation, FMS managed rule groups, FMS OU targeting, FMS policy
priority, FMS resource tags.

## STRICT output contract

When this skill is invoked with a Firewall-Manager-provisioning request
(create an FMS policy, set up managed WAF rules across an Organization,
enforce security group policies centrally, deploy Network Firewall at
scale, or configure Shield Advanced org-wide), the agent MUST respond
with the READY_TO_DEPLOY checklist defined in the "Output format" section
using the literal all-caps labels `FMS_POLICY:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist
with prose, headings, or disclaimers — emit the block as the first lines
of the response. This contract is what assertion-based evals and
downstream provisioning pipelines rely on; deviating from the literal
labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Administrator account delegation | FMS setup |
| Step 2 — Policy type selection (WAF, SG, NFW, Shield) | Core policy model |
| Step 3 — AWS Organizations targeting (OU vs account) | Scope |
| Step 4 — Remediation mode (auto-apply vs monitor-only) | Enforcement |
| Step 5 — WAF managed rule group association | WAF policies |
| Step 6 — Security group policies (common vs content audit) | SG policies |
| Step 7 — Network Firewall policy deployment | NFW policies |
| Step 8 — Shield Advanced policy deployment | Shield policies |
| Step 9 — Resource tag inclusion/exclusion | Resource scoping |
| Step 10 — Policy priority ordering | Evaluation order |
| Step 11 — Compliance monitoring via AWS Config | Compliance posture |
| Step 12 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/policy-types-and-remediation.md | Policy type + remediation detail |
| references/targeting-and-priority.md | OU targeting + priority detail |

## Mindset

**One-line takeaway:** AWS Firewall Manager is an Organization-level
orchestration layer that deploys and enforces firewall policies (WAF,
Security Groups, Network Firewall, Shield Advanced) across member
accounts. Policies are evaluated in priority order (first-match wins).
Remediation can be auto-apply (noncompliant resources are fixed) or
monitor-only (violations are reported but not fixed). The FMS
administrator account must be delegated before any policy can be
created.

Three misconceptions dominate FMS misdesign at provisioning time:

- **"Creating a WAF Web ACL is the same as an FMS WAF policy."** It is
  not. A standalone WAF Web ACL lives in one account and is attached
  to resources in that account. An FMS WAF policy creates and manages
  Web ACLs across ALL targeted accounts (an entire OU or the whole
  Organization) — the policy is the source of truth; individual Web
  ACLs are read-only in member accounts. Editing a managed Web ACL
  directly in a member account will be reverted by FMS remediation.

- **"Monitor-only and auto-apply remediation behave the same way."**
  They do NOT. Monitor-only (RemediationEnabled=false) flags
  noncompliant resources in the FMS console and via Config but does NOT
  fix them. Auto-apply (RemediationEnabled=true) automatically creates
  or modifies resources to comply (e.g., attaches the managed Web ACL
  to new ALBs, applies security groups to ENIs). A grace period (in
  days) can be set so that resources are noncompliant for N days before
  auto-remediation kicks in.

- **"Policy priority does not matter because each resource is targeted
  by one policy."** It DOES matter. A resource can be in scope of
  multiple FMS policies (e.g., a WAF policy and a security group
  policy). Within a single policy type (e.g., multiple WAF policies),
  FMS evaluates in priority order — the first matching policy wins.
  Lower priority policies are NOT applied to resources already covered
  by a higher-priority policy. Policy priority ordering is critical for
  layered security designs.

## Configuration dependency graph (novel heuristic)

FMS policy configurations are NOT independent. The administrator
account must be delegated before policies can be created. AWS
Organizations must be enabled for OU-based targeting. AWS Config must
be enabled in member accounts for compliance evaluation. Remediation
mode interacts with the grace period. Use this graph to sequence
provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| FMS admin account | AWS Organizations enabled; management account or delegated admin | once set, the admin account is the ONLY account that can manage policies | all FMS policies |
| AWS Organizations integration | Organizations enabled; all member accounts invited | policies targeting an OU only apply to accounts INSIDE the Organization | OU-based policy scope |
| AWS Config (member accounts) | Config recorder active in each member account | without Config, FMS cannot evaluate compliance; resources show as unknown | compliance status reporting |
| Policy creation | FMS admin account delegated; policy type supported in the Region | once created, the policy priority is fixed unless explicitly reordered | enforcement across member accounts |
| WAF managed rule groups | WAF policy type selected; managed rule group available in Region | managed rule group version pinning prevents silent rule updates | WAF rule enforcement |
| Security group policy (common) | SG policy type selected; at least one baseline SG defined | common mode applies the SAME SG rules to all targeted resources | SG enforcement |
| Security group policy (content audit) | SG policy type selected; audit rules defined | content audit mode checks existing SGs against audit rules; nonconforming SGs are flagged/remediated | SG compliance checking |
| Network Firewall policy | NFW policy type selected; firewall subnet mappings defined | NFW policies require subnet mappings in each target account for firewall placement | managed Network Firewalls |
| Shield Advanced policy | Shield Advanced enabled; protected resources supported | Shield Advanced coverage is automatic for supported resource types in targeted accounts | DDoS protection |
| Remediation (auto-apply) | policy created; RemediationEnabled=true | grace period (days) delays auto-fix; during the grace period resources are noncompliant but not remediated | automatic enforcement |
| Resource tag inclusion/exclusion | policy created; tag keys defined | exclude tags take precedence over include tags; a resource with an exclude tag is NEVER targeted | resource scoping |
| Policy priority | at least two policies of the same type | priority is evaluated first-match wins; changing priority requires reordering | evaluation order |

**The remediation-grace-period row is the one a baseline model misses.**
Creating a policy with RemediationEnabled=true is necessary but the
grace period determines WHEN auto-remediation starts. A grace period of
0 means immediate remediation; 7 days means resources have a week to
become compliant before being force-fixed. The procedure below forces an
explicit decision on remediation mode and grace period.

**Cross-dependency gotchas:**
- The FMS administrator account CANNOT also be a target account. If
  the admin account is inside the OU you are targeting, exclude it via
  account-level exclusion or move it outside the OU.
- Policy priority is per-type. A WAF policy at priority 1 and a
  security group policy at priority 1 do NOT conflict — they are
  different types. Two WAF policies at priority 1 DO conflict; FMS
  evaluates the lower-numbered one first.
- Exclude tags override include tags. A resource with BOTH an include
  tag and an exclude tag is excluded.
- AWS Config MUST be enabled in every member account for FMS to report
  compliance. Without Config, resources show as "unknown" compliance,
  not "compliant."

## Expert heuristic: policy priority evaluation order (first-match wins)

First-match-wins evaluation model with worked overlap examples moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § Expert heuristic: policy priority evaluation order

## Expert heuristic: OU scope vs account scope expansion

OU auto-expansion semantics (future accounts, IncludeMap/ExcludeMap interplay) moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § Expert heuristic: OU scope vs account scope expansion

## Expert heuristic: remediation grace period

Auto-apply vs monitor-only behavior and grace-period timing model moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § Expert heuristic: remediation grace period

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS Organizations enabled | FMS requires Organizations for multi-account management | `aws organizations describe-organization` |
| FMS administrator account delegated | Only the admin account can create policies | `aws fms get-admin-account` |
| AWS Config enabled in member accounts | FMS needs Config for compliance evaluation | `aws configservice describe-configuration-recorders` (in each member) |
| Supported Region | FMS is not available in all Regions | `aws fms list-policies --region <region>` (no error = supported) |
| Policy type supported | Some types (Shield Advanced) need additional enablement | Verify the service is enabled in the admin account |
| Target OU/account IDs identified | Scope determines which accounts are affected | `aws organizations list-roots` / `list-organizational-units-for-parent` |
| Managed rule group ARN (WAF) | WAF policies need a pre-existing rule group or managed rule set | `aws wafv2 list-managed-rule-sets --scope REGIONAL` |
| Baseline security group (SG policy) | Common SG policies need a reference SG | `aws ec2 describe-security-groups --group-ids <sg-id>` |
| Resource tag keys identified | Inclusion/exclusion tags scope which resources are targeted | Confirm tag keys exist on target resources |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Administrator account delegation

The FMS administrator account is the single account that manages all FMS
policies. It must be delegated before any policy can be created.

| Action | API call |
|---|---|
| Delegate admin account | `aws fms associate-admin-account` |
| Verify admin account | `aws fms get-admin-account` |
| List member accounts (compliance) | `aws fms list-member-accounts` |

**Delegate the FMS admin account:**

```bash
aws fms associate-admin-account \
  --admin-account 111111111111 \
  --region us-east-1
```

**Verify:**

```bash
aws fms get-admin-account --region us-east-1
# Expected: { AdminAccount: "111111111111" }
```

**Common mistake:** trying to create policies from an account that is
NOT the delegated admin. The API returns an error.

## Step 2 — Policy type selection (WAF, SG, NFW, Shield)

FMS supports four primary policy types. Each type has different resource
targets and configuration requirements.

| Policy Type | AWS Service | Targets | Key Config |
|---|---|---|---|
| WAF | AWS WAF | ALB, API Gateway, AppSync, CloudFront, Cognito, App Runner | Managed rule groups, custom rules |
| Security Group | EC2 / VPC | EC2 ENIs, ALB | Common SG or content audit rules |
| Network Firewall | AWS Network Firewall | VPC subnets | Firewall subnet mappings, rule groups |
| Shield Advanced | AWS Shield Advanced | ALB, NLB, CloudFront, Route53, Global Accelerator | Protected resource auto-coverage |

**Policy type selection decision:**

```text
What are you protecting?
  ├── Web apps (ALB, API Gateway, CloudFront)
  │     → WAF policy with managed rule groups
  ├── EC2 instances / ENIs
  │     → Security Group policy (common or content audit)
  ├── VPC-level network traffic (east-west, north-south)
  │     → Network Firewall policy
  └── DDoS protection for internet-facing resources
        → Shield Advanced policy
```

## Step 3 — AWS Organizations targeting (OU vs account)

FMS policies can target the entire Organization, specific OUs, or
individual accounts.

| Scope | IncludeMap | Behavior |
|---|---|---|
| Entire Organization | `{"ROOT": ["r-xxxx"]}` | All accounts, including future |
| Specific OU | `{"ORG_UNIT": ["ou-xxxx-yyyy"]}` | Accounts in the OU, including future additions |
| Individual accounts | `{"ACCOUNT": ["111111111111"]}` | Only listed accounts (no auto-expansion) |

**Exclude resources or accounts:**

Use `ExcludeResourceTags` or `ExcludeAccounts` to narrow scope.

```text
Include: OU=Workloads (accounts: 111, 222, 333)
Exclude: Accounts: 333 (sensitive workload)
Result: Policy applies to accounts 111 and 222 only
```

## Step 4 — Remediation mode (auto-apply vs monitor-only)

| Mode | RemediationEnabled | Behavior |
|---|---|---|
| Monitor-only | `false` | Report noncompliance, NO auto-fix |
| Auto-apply | `true` | Automatically create/modify resources to comply |
| Auto-apply with grace | `true` + `RemediationGracePeriodDays` | Wait N days before auto-fixing |

**Decision framework:**

```text
New policy → start monitor-only (RemediationEnabled=false)
  → evaluate compliance posture for 1-2 weeks
  → transition to auto-apply with grace period (7 days)
  → tighten to 0-day grace once stable
```

## Step 5 — WAF managed rule group association

Full WAF policy configuration (managed rule groups, pre/post rule sets, remediation) moved to references.
→ [references/policy-types-and-remediation.md](references/policy-types-and-remediation.md) § Step 5 — WAF managed rule group association

## Step 6 — Security group policies (common vs content audit)

SG common vs content-audit mode table and ManagedServiceData structure moved to references.
→ [references/policy-types-and-remediation.md](references/policy-types-and-remediation.md) § Step 6 — Security group policies

## Step 7 — Network Firewall policy deployment

Network Firewall policy configuration (firewall subnet mappings, rule groups) moved to references.
→ [references/policy-types-and-remediation.md](references/policy-types-and-remediation.md) § Step 7 — Network Firewall policy deployment

## Step 8 — Shield Advanced policy deployment

Shield Advanced policy configuration and coverage behavior moved to references.
→ [references/policy-types-and-remediation.md](references/policy-types-and-remediation.md) § Step 8 — Shield Advanced policy deployment

## Step 9 — Resource tag inclusion/exclusion

FMS policies can scope resources by tags. Include tags narrow the
resource set; exclude tags override include tags.

| Tag Type | Behavior | Field |
|---|---|---|
| Include tags | Only resources with these tags are targeted | `IncludeResourceTags` |
| Exclude tags | Resources with these tags are NEVER targeted | `ExcludeResourceTags` |

```text
Include tags: Environment=production
Exclude tags: ComplianceExempt=true

Result:
  Resource with Environment=production, no exclude tag → TARGETED ✓
  Resource with Environment=production, ComplianceExempt=true → EXCLUDED ✗
  Resource with Environment=dev → NOT targeted (include tag mismatch)
```

## Step 10 — Policy priority ordering

Priority-conflict resolution workflow and reorder commands moved to references.
→ [references/targeting-and-priority.md](references/targeting-and-priority.md) § Step 10 — Policy priority ordering

## Step 11 — Compliance monitoring via AWS Config

FMS reports compliance status via AWS Config. Each policy evaluates
resources and reports compliance (COMPLIANT, NON_COMPLIANT, or
INFORMATIONAL).

```bash
# Get compliance status for a policy
aws fms get-compliance-detail \
  --policy-id <policy-id> \
  --member-account <account-id> \
  --region us-east-1

# List non-compliant accounts
aws fms list-compliance-status \
  --policy-id <policy-id> \
  --region us-east-1
```

**Compliance states:**

| State | Meaning |
|---|---|
| COMPLIANT | Resource meets the policy requirements |
| NON_COMPLIANT | Resource violates the policy |
| INFORMATIONAL | Resource is being evaluated or is exempt |

## Step 12 — Recent features

2023-2026 FMS feature notes moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § Step 12 — Recent features

## NEVER do these things

1. **NEVER create an FMS policy without delegating the admin account
   first.** The `put-policy` API returns an AccessDeniedException if the
   calling account is not the delegated FMS administrator. Always verify
   with `get-admin-account` before creating policies.

2. **NEVER assume monitor-only and auto-apply behave the same way.**
   Monitor-only reports violations; auto-apply fixes them. Starting
   with auto-apply on a new policy can cause unexpected resource
   changes across ALL targeted accounts. Always start with monitor-only.

3. **NEVER ignore policy priority when multiple policies of the same
   type exist.** FMS evaluates first-match wins. A lower-priority policy
   silently does NOT apply to resources covered by a higher-priority
   policy. Always verify priority ordering.

4. **NEVER target the FMS admin account with its own policies.** The
   admin account cannot be both manager and target. If the admin
   account is inside a targeted OU, exclude it explicitly.

5. **NEVER assume exclude tags and include tags are symmetric.** Exclude
   tags ALWAYS override include tags. A resource with both is excluded.
   This is the most common tag-scoping surprise.

6. **NEVER forget that FMS-managed Web ACLs are read-only in member
   accounts.** Editing a Web ACL that FMS manages will be reverted on
   the next remediation cycle. All changes must go through the FMS
   policy in the admin account.

7. **NEVER deploy a Network Firewall policy without subnet mappings in
   target accounts.** Network Firewall policies require firewall subnet
   mappings for firewall placement. Without subnets, the policy deploys
   but no firewall is created.

8. **NEVER assume AWS Config is automatically enabled in member
   accounts.** FMS relies on Config for compliance evaluation. If Config
   is not enabled in a member account, resources show as "unknown"
   compliance, not "compliant."

9. **NEVER set RemediationGracePeriodDays without understanding the
   impact.** A 0-day grace means immediate auto-fix; 7 days means a
   week of noncompliance before fixing. Choose based on risk tolerance.

10. **NEVER use a standalone WAF Web ACL ARN as a managed rule group.**
    FMS creates the Web ACLs; you specify the rule groups. Confusing
    these will result in an invalid policy configuration.

## Output format

```text
FMS_POLICY: <policy-name> (type: <WAFV2|SECURITY_GROUPS_COMMON|SECURITY_GROUPS_CONTENT_AUDIT|NETWORK_FIREWALL|SHIELD_ADVANCED>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] FMS admin account: <account-id> (delegated)
  [✓|✗] AWS Organizations: enabled (management account <mgmt-acct-id>)
  [✓|✗] AWS Config: enabled in all target accounts
  [✓|✗] Policy type: <type>
  [✓|✗] Target scope: <OU|ACCOUNT|ORG> (<id-list>)
  [✓|✗] Remediation: <monitor-only|auto-apply (grace: <N> days)>
  [✓|✗] Managed rule groups: <list> (WAF policies)
  [✓|✗] Security group: <baseline-sg-id> (common) | audit rules (content audit)
  [✓|✗] Network Firewall subnets: <subnet-mappings> (NFW policies)
  [✓|✗] Include tags: <key=value list>
  [✓|✗] Exclude tags: <key=value list>
  [✓|✗] Policy priority: <number> (evaluation order)
  [✓|✗] Compliance reporting: AWS Config (COMPLIANT|NON_COMPLIANT|INFORMATIONAL)
VERIFICATION_COMMANDS:
  aws fms list-policies --region <region>
  aws fms get-policy --policy-id <policy-id> --region <region>
  aws fms list-compliance-status --policy-id <policy-id> --region <region>
  aws fms get-admin-account --region <region>
```

### Worked example — WAF policy targeting the Prod OU with auto-remediation

```text
FMS_POLICY: org-waf-common-rules (type: WAFV2)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] FMS admin account: 111111111111 (delegated)
  [✓] AWS Organizations: enabled (management account 000000000000)
  [✓] AWS Config: enabled in all target accounts
  [✓] Policy type: WAFV2
  [✓] Target scope: ORG_UNIT (ou-prod-abcdef)
  [✓] Remediation: auto-apply (grace: 7 days)
  [✓] Managed rule groups: AWSManagedRulesCommonRuleSet, AWSManagedRulesKnownBadInputsRuleSet
  [✓] Include tags: Environment=production
  [✓] Exclude tags: ComplianceExempt=true
  [✓] Policy priority: 1 (first-match evaluation)
  [✓] Compliance reporting: AWS Config (COMPLIANT|NON_COMPLIANT|INFORMATIONAL)
VERIFICATION_COMMANDS:
  aws fms list-policies --region us-east-1
  aws fms get-policy --policy-id <policy-id> --region us-east-1
  aws fms list-compliance-status --policy-id <policy-id> --region us-east-1
  aws fms get-admin-account --region us-east-1
```

## Error handling

Error deep dives (AccessDenied on put-policy, unknown compliance, reverted changes, priority conflicts, missing NFW) moved to references.
→ [references/error-handling.md](references/error-handling.md) § Error handling

## References (load on demand)

Consult these only when the corresponding topic comes up:

- [references/policy-types-and-remediation.md](references/policy-types-and-remediation.md) — policy-type configurations moved from Steps 5-8 (WAF, SG, Network Firewall, Shield)
- [references/targeting-and-priority.md](references/targeting-and-priority.md) — OU/account scope detail and the Step 10 priority-ordering workflow
- [references/error-handling.md](references/error-handling.md) — failure modes moved from § Error handling
- [references/advanced-patterns.md](references/advanced-patterns.md) — expert heuristics (priority order, OU scope, grace period) and recent AWS features

## Domain

AWS CloudOps / AWS Firewall Manager Policy Provisioning & Organization-
Wide Security Enforcement.

## AWS documentation

- **Firewall Manager Guide** — https://docs.aws.amazon.com/waf/latest/developerguide/fms-chapter.html
- **FMS policies** — https://docs.aws.amazon.com/waf/latest/developerguide/fms-policies.html
- **FMS administrator account** — https://docs.aws.amazon.com/waf/latest/developerguide/fms-admin-account.html
- **FMS WAF policies** — https://docs.aws.amazon.com/waf/latest/developerguide/fms-waf-policies.html
- **FMS security group policies** — https://docs.aws.amazon.com/waf/latest/developerguide/fms-security-group-policies.html
- **FMS Network Firewall policies** — https://docs.aws.amazon.com/waf/latest/developerguide/fms-network-firewall-policies.html
- **FMS Shield Advanced policies** — https://docs.aws.amazon.com/waf/latest/developerguide/fms-shield-advanced-policies.html
- **FMS remediation** — https://docs.aws.amazon.com/waf/latest/developerguide/fms-remediation.html
- **FMS compliance** — https://docs.aws.amazon.com/waf/latest/developerguide/fms-compliance.html
- **FMS policy priority** — https://docs.aws.amazon.com/waf/latest/developerguide/fms-policy-priority.html
