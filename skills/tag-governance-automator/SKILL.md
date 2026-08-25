---
name: tag-governance-automator
description: 'Designs and implements AWS tag governance automation across Organizations TagPolicy JSON (allowed_values, case_sensitive, enforced_for cascade), EventBridge + Lambda auto-tagging on EC2/S3/Lambda creation (derive Owner from IAM identity, Environment from account map), Resource Groups Tagging API bulk operations (tag-resources, untag-resources, get-resources multi-region), Config required-tags managed rule + Security Hub finding aggregation, cost-allocation-tag activation via Billing API (user-defined vs AWS-generated), and ABAC IAM policy design with aws:ResourceTag and aws:PrincipalTag condition keys. Covers automated remediation: Config detects missing tag, SSM Automation adds tag, Config re-evaluates. Emits AUTOMATED with tag policy template or MANUAL_STEP_REQUIRED with the specific gap. Use when building tag governance, auto-tagging pipelines, ABAC, or tag-compliance automation.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline policy design. Live deployment uses aws organizations enable-policy-type, create-policy, update-policy, aws resourcegroupstaggingapi tag-resources, untag-resources, get-resources, aws configservice put-config-rule, describe-config-rules, aws ce update-cost-allocation-tags-status, aws ssm create-document, start-automation-execution, and aws lambda create-function with an...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Governance
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: AUTOMATED | MANUAL_STEP_REQUIRED
  when_to_use: Designing Organizations tag policies (allowed_values, case sensitivity, enforced_for), building EventBridge + Lambda auto-tagging pipelines, running Resource Groups Tagging API bulk operations across regions, wiring Config required-tags rules with Security Hub findings, activating cost allocation tags, designing ABAC IAM policies with aws:ResourceTag / aws:PrincipalTag conditions, or remediating untagged resources via Config + SSM Automation.
  activation_triggers: design Organizations TagPolicy, allowed_values enforced_for, auto-tag on creation EventBridge Lambda, Resource Groups Tagging API bulk, tag-resources untag-resources, required-tags Config rule, cost allocation tag activation, ABAC IAM policy ResourceTag, tag compliance remediation, Security Hub tag finding, tag governance baseline
  invocation_schema: 'Input: either (a) a tag governance requirement ("enforce Environment and CostCenter tags on all EC2 and S3 resources", "auto-tag Owner on EC2 creation", "design ABAC policy for team-scoped access"), OR (b) an existing tag policy / Config rule / EventBridge rule to audit and harden. Output: deterministic GOVERNANCE block per requirement — STRATEGY/POLICY/AUTOMATION/COMPLIANCE/VERDICT — where VERDICT is AUTOMATED (tag policy template ready) or MANUAL_STEP_REQUIRED (specific gap cited, e.g., Billing console activation that cannot be API-driven).'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: AWS Organizations, Tag Policy, TagPolicy, allowed_values, enforced_for, Resource Groups Tagging API, tag-resources, untag-resources, AWS Config, required-tags, Security Hub, EventBridge, Lambda auto-tagging, cost allocation tags, ABAC, aws:ResourceTag, aws:PrincipalTag, aws:RequestTag, SSM Automation, tag compliance, tag governance
  tags: aws-organizations, tag-policy, resource-groups-tagging-api, aws-config, security-hub, abac, eventbridge, lambda, automate
---

# Tag Governance Automator

## Mindset

**One-line takeaway:** tag governance is a three-layer stack — **define**
(Organizations TagPolicy sets the rules) → **enforce** (EventBridge +
Lambda auto-tags on creation; Config required-tags detects violations) →
**remediate** (SSM Automation or Lambda adds missing tags; Config
re-evaluates and flips COMPLIANT). A gap in ANY layer produces a silent
failure: the policy is published but never enforced, resources are tagged
inconsistently, cost allocation reports are wrong, and ABAC policies
silently over-permit or under-permit.

- **Organizations TagPolicy** without `enforced_for` is advisory only:
  the policy says Environment must be `prod` or `dev`, but if no resource
  type is listed under `enforced_for`, AWS does not block non-compliant
  tag operations. The policy is documentation, not enforcement.
- **Auto-tagging** without a **tag policy** produces drift: the Lambda
  stamps tags on creation, but nothing stops a human from changing them
  afterward. Always pair auto-tagging with a tag policy that prevents
  unauthorized modifications.
- **Cost allocation tags are NOT active by default.** A perfectly tagged
  fleet produces zero cost-dimension data in CUR / Cost Explorer until
  an administrator activates the tag keys in Billing. This is the #1
  "we tagged everything and Cost Explorer is still empty" issue.

## Quick navigation

| You want to... | Go to |
|---|---|
| Define required vs optional tag keys | Step 1 (tag strategy table) |
| Author Organizations TagPolicy JSON | Step 2 + Appendix A |
| Build EventBridge + Lambda auto-tagging | Step 3 + reference auto-tagging-eventbridge-lambda.md |
| Bulk tag/untag across regions via Tagging API | Step 4 |
| Wire Config `required-tags` rule | Step 5 |
| Route tag findings to Security Hub | Step 6 |
| Remediate missing tags automatically (Config → SSM → Config) | Step 7 |
| Activate cost allocation tags | Step 8 |
| Design ABAC IAM policies (aws:ResourceTag / aws:PrincipalTag) | Step 9 |
| Verify and audit a deployed governance baseline | Step 10 |
| Avoid common tag-policy and ABAC pitfalls | Anti-Patterns |
| Recent features (TagPolicy ABAC, CE tag-status API) | Recent AWS features |

## Critical rules at a glance (do NOT bury these)

1. **`enforced_for` is what makes a tag policy enforce.** Without it,
   the policy defines allowed values but AWS does not block non-compliant
   `CreateTags` / `PutBucketTagging` / `TagResource` calls. A policy
   with `allowed_values` but no `enforced_for` is a recommendation, not
   a guardrail. Always list the resource types explicitly.
2. **Organizations TagPolicy `allowed_values` matching is case-insensitive
   by default.** Set `tag_key.case_sensitive: true` if your downstream
   systems (CUR, ABAC conditions) depend on exact casing. A mismatch
   between the policy's case sensitivity and your IAM `StringEquals`
   conditions produces silent ABAC over-grants.
3. **Tag policies cascade: org root → OU → account → resource.** A
   child policy does NOT override the parent — it is additive (union of
   constraints). You cannot relax a parent's `allowed_values` at the
   child level. If the root says Environment is `prod|dev`, an OU
   cannot add `staging` without editing the root policy.
4. **Cost allocation tags require explicit activation in Billing.**
   Tagging a resource does NOT make the tag appear in Cost Explorer or
   the Cost and Usage Report (CUR). An administrator must activate each
   tag key via the Billing console or `ce update-cost-allocation-tags-status`.
   Activation takes up to 24 hours to propagate.
5. **ABAC condition keys are case-sensitive at the IAM evaluation layer.**
   `aws:ResourceTag/Environment` with `StringEquals: "prod"` does NOT
   match a resource tagged `Prod`. If your tag policy allows
   case-insensitive values but your IAM condition uses `StringEquals`,
   you have a silent gap. Use `StringEqualsIgnoreCase` for ABAC
   conditions OR enforce case sensitivity in the tag policy.

## Pre-flight: data requirements

Designing a tag governance baseline requires these inputs:

| Input | Source | Why |
|---|---|---|
| Organization ID + root ID | `aws organizations describe-organization` | Tag policy scope |
| Existing tag policies | `aws organizations list-policies --filter TAG_POLICY` | Don't overwrite blindly |
| OU structure | `aws organizations list-organizational-units-for-parent` | Where to attach policies |
| Account → environment mapping | Internal CMDB or account tags | Drives `Environment` allowed_values |
| Config recorder status | `aws configservice describe-configuration-recorders` | Required-tags rule needs recorder |
| Existing Config rules | `aws configservice describe-config-rules` | Avoid duplicate required-tags rules |
| Security Hub enablement | `aws securityhub describe-hub` | Finding aggregation target |
| Sample resource inventory | `aws resourcegroupstaggingapi get-resources` | Baseline current tag coverage |
| IAM principal tags (for ABAC) | `aws iam list-user-tags` / `list-role-tags` | ABAC source attributes |

**If the input is malformed** (missing org ID, ambiguous scope), emit:

```text
GOVERNANCE: <reference>
VERDICT: ERROR
REASON: Cannot design tag governance — Organizations root ID and target scope (resource types + accounts) are required.
GAP: Re-supply describe-organization output and the list of resource types to enforce tagging on.
```

## Process — Workflow design (apply in order)

### Step 0: Expert knowledge — non-obvious TagPolicy + tagging behaviors

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-0-expert-knowledge--non-obvious-tagpolicy--tagging-behaviors).
> Ten expert behaviors: enforcement only on enforced_for types, service:resource-type notation typos silently disable enforcement, policies block but never retro-fix, tag-resources is not atomic (check FailedResourcesMap), get-resources is region-scoped, required-tags max 5 keys, cost-tag activation is per-account, aws:PrincipalTag resolves at session creation, aws:RequestTag is create/tag-only, per-type tagging APIs need branching runbooks, system tags are not enforced.

### Step 1: Define the tag strategy framework

Every governance engagement starts with a canonical tag key set.
Default to this baseline and adjust per organizational requirements:

| Tag key | Category | Required? | Allowed values (example) | Purpose |
|---|---|---|---|---|
| `Environment` | Required | Yes | `dev`, `staging`, `prod` | ABAC, cost split, blast-radius scoping |
| `Owner` | Required | Yes | email or team alias (free-form) | Accountability, alert routing |
| `Project` | Required | Yes | project code (free-form) | Cost allocation |
| `CostCenter` | Required | Yes | `cc-1001`, `cc-1002`, ... | Finance reporting |
| `Application` | Required | Yes | app name (free-form) | Grouping, dependency mapping |
| `Backup:Required` | Optional | No | `true`, `false` | Backup policy routing |
| `ComplianceTier` | Optional | No | `tier-1`, `tier-2`, `tier-3` | Audit cadence, SOC scope |
| `DataClassification` | Optional | No | `public`, `internal`, `confidential` | Macie, KMS routing |

**Decision rules:**
- Never exceed 10 required tags — operational friction kills adoption.
- Free-form tags (`Owner`, `Project`) are acceptable for the FIRST pass;
  tighten to allowed_values once the set stabilizes.
- Map each tag key to a downstream consumer (Cost Explorer, ABAC, Config,
  Macie). A tag no consumer reads is dead weight.

### Step 2: Author the Organizations TagPolicy JSON

> Moved to [references/organizations-tag-policies.md](references/organizations-tag-policies.md#step-2-author-the-organizations-tagpolicy-json-moved-from-skillmd).
> Full recipe: enable-policy-type, the canonical baseline TagPolicy JSON (Environment/CostCenter/Owner/Project with case_sensitive + allowed_values + enforced_for), create-policy, attach to root/OU, negative-test enforcement, and the common-errors table (TagPolicyViolationException, silent no-enforcement, additive child limits, PolicyTypeNotEnabledException).

### Step 3: Build EventBridge + Lambda auto-tagging

> Moved to [references/auto-tagging-eventbridge-lambda.md](references/auto-tagging-eventbridge-lambda.md#step-3-build-eventbridge--lambda-auto-tagging-moved-from-skillmd).
> Full recipe: CloudTrail → EventBridge rule (EC2 RunInstances; S3 CreateBucket + Lambda CreateFunction) → the multi-service Python handler with account→Environment mapping, plus the Lambda execution-role permissions and the EventBridge-vs-SSM trade-off table.

### Step 4: Resource Groups Tagging API bulk operations

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-4-resource-groups-tagging-api-bulk-operations).
> Bulk tag/untag, multi-region get-resources iteration, get-tag-keys/values, FailedResourcesMap discipline, and the Tag Editor console alternative (manual-only, never the primary mechanism).

### Step 5: Wire Config `required-tags` managed rule

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-5-wire-config-required-tags-managed-rule).
> required-tags-core put-config-rule CLI (5 keys, 4 resource types), the required-tags-ext second rule for 6+ keys, and describe/get-compliance verification.

### Step 6: Security Hub integration

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-6-security-hub-integration).
> FSBP tag controls ([EC2.26]/[S3.10]/[Lambda.3]), enable-security-hub, describe-standards-controls tag query, and the batch-import-findings custom-finding payload.

### Step 7: Automated remediation (Config → SSM → Config re-evaluate)

> Moved to [references/worked-examples.md](references/worked-examples.md#step-7-automated-remediation-config--ssm--config-re-evaluate).
> Pattern A: the Custom-AddRequiredTagsEC2 SSM Automation YAML + put-remediation-configurations wiring (Automatic: false); Pattern B: EventBridge on Config NON_COMPLIANT → Lambda; placeholder remediation requires a human-correction queue.

### Step 8: Activate cost allocation tags

Cost allocation tags do NOT appear in Cost Explorer or CUR until
activated. Two activation paths:

**Path A — API (preferred for automation):**

```bash
aws ce update-cost-allocation-tags-status \
  --cost-allocation-tags-status \
    '[{"TagKey":"Environment","Status":"Active"},
      {"TagKey":"Owner","Status":"Active"},
      {"TagKey":"Project","Status":"Active"},
      {"TagKey":"CostCenter","Status":"Active"}]'
```

Verify:

```bash
aws ce list-cost-allocation-tags \
  --status Active
```

**Path B — Billing console (fallback):**

```
Billing console → Cost Allocation Tags → user-defined cost allocation tags
→ Activate each tag key.
```

**User-defined vs AWS-generated tags:**

| Tag source | Examples | Activation |
|---|---|---|
| User-defined | `Owner`, `Environment`, `Project` | Must be activated manually |
| AWS-generated | `aws:createdBy`, `aws:cloudformation:stack-name` | `aws:createdBy` is auto-active; others must be activated |

**Org payer vs member accounts:** in a consolidated billing family,
activate tags on the payer account. The payer's cost allocation tag
settings apply to the consolidated CUR. Member-account-specific tags
require per-member activation for member-account-local reporting.

If the account does NOT support `ce update-cost-allocation-tags-status`
(legacy accounts or restricted IAM), the activation is a MANUAL step.
Flag `MANUAL_STEP_REQUIRED` with the Billing-console path.

### Step 9: ABAC IAM policy design

Attribute-based access control uses resource and principal tags in IAM
condition keys to make access decisions. ABAC scales better than RBAC
for large orgs because new resources and principals inherit access from
their tags — no policy edit needed.

**ABAC condition keys:**

| Condition key | Source | When evaluated |
|---|---|---|
| `aws:ResourceTag/<key>` | Resource tags | On every API call against the resource |
| `aws:PrincipalTag/<key>` | IAM user/role session tags | At session creation (fixed for session lifetime) |
| `aws:RequestTag/<key>` | Tags in the API request | On create / tag operations only |
| `aws:TagKeys` | List of tag keys in request | On tag operations |

**ABAC policy pattern (team-scoped S3 access):**


> Policy JSON moved to [references/worked-examples.md](references/worked-examples.md#abac-policy-pattern--team-scoped-s3-access-moved-from-skillmd).
> Two statements: team-tag-gated object actions on team-data-* plus CreateBucket with aws:RequestTag/Team and ForAllValues aws:TagKeys allow-list.

**ABAC prerequisites checklist:**
1. IAM principals (users / roles) are tagged with the attribute (e.g., `Team`).
2. Resources are tagged with the same attribute.
3. The IAM policy uses `aws:ResourceTag` matching `aws:PrincipalTag`.
4. The tag policy (Step 2) enforces that the attribute tag key exists on
   new resources (otherwise ABAC silently breaks for new resources).
5. Session tags are passed on `AssumeRole` via `--tags` or STS session
   tagging.

**Common ABAC pitfall:** `StringEquals` is case-sensitive. If your tag
policy allows `case_sensitive: false` for `Environment`, but your IAM
condition is `StringEquals: {"aws:ResourceTag/Environment": "prod"}`,
a resource tagged `Prod` fails the check. Either enforce
`case_sensitive: true` in the tag policy OR use
`StringEqualsIgnoreCase` in the IAM condition.

### Step 10: Audit and verify a deployed governance baseline

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-10-audit-and-verify-a-deployed-governance-baseline).
> Six verification groups: tag policy attached/enforced, Config rule evaluating, auto-tagger Lambda firing, Security Hub findings, active cost allocation tags, resource tag coverage — plus the "passes 1-3 but zero cost tags = incomplete" rule.

## STRICT output contract

Every output MUST follow this exact structure. Deviations are bugs in
the skill.

```text
GOVERNANCE: <reference>
SCOPE: <accounts / OUs / regions covered>
STRATEGY:
  - Required tags: <comma-separated keys>
  - Optional tags: <comma-separated keys or "none">
  - Enforcement layer: <Organizations TagPolicy | Config rule | both>
POLICY:
  - Type: <Organizations TagPolicy | Config required-tags | EventBridge auto-tagger | ABAC IAM | conformance pack>
  - Attached to: <root | OU | account | resource>
  - Template: <inline JSON/YAML or "see Step N">
AUTOMATION:
  - Auto-tagging: <EventBridge + Lambda | none>
  - Remediation: <SSM Automation | Lambda | none>
  - Trigger: <automatic | manual>
COMPLIANCE:
  - Detection: <Config rule name(s)>
  - Reporting: <Security Hub | Config dashboard | both>
  - Cost allocation: <active | inactive | pending>
VERDICT: AUTOMATED | MANUAL_STEP_REQUIRED
GAP: <if MANUAL_STEP_REQUIRED, the specific missing piece>
TEMPLATE: <full CLI snippet or policy JSON>
```

### Worked example — AUTOMATED, full tag governance baseline

```text
GOVERNANCE: org-tag-baseline
SCOPE: org root r-xxxx, all member accounts, us-east-1 + us-west-2
STRATEGY:
  - Required tags: Environment, Owner, Project, CostCenter, Application
  - Optional tags: Backup:Required, ComplianceTier, DataClassification
  - Enforcement layer: Organizations TagPolicy + Config required-tags rule
POLICY:
  - Type: Organizations TagPolicy + Config required-tags-core
  - Attached to: root (policy), Config recorder (rule)
  - Template: see Step 2 (TagPolicy JSON) + Step 5 (Config rule)
AUTOMATION:
  - Auto-tagging: EventBridge + Lambda on RunInstances, CreateBucket, CreateFunction
  - Remediation: SSM Automation Custom-AddRequiredTagsEC2 (manual trigger, placeholder values)
  - Trigger: manual (placeholder remediation requires human correction)
COMPLIANCE:
  - Detection: required-tags-core, required-tags-ext
  - Reporting: Security Hub FSBP controls + Config compliance dashboard
  - Cost allocation: active (Environment, Owner, Project, CostCenter via ce API)
VERDICT: AUTOMATED
GAP: None
TEMPLATE:
  aws organizations create-policy --type TAG_POLICY --name baseline-tag-policy --content file://tag-policy.json
  aws configservice put-config-rule --config-rule '{"ConfigRuleName":"required-tags-core","Source":{"Owner":"AWS","SourceIdentifier":"REQUIRED_TAGS"},"Scope":{"ComplianceResourceTypes":["AWS::EC2::Instance","AWS::S3::Bucket","AWS::Lambda::Function","AWS::RDS::DBInstance"]},"InputParameters":"{\"tag1Key\":\"Environment\",\"tag2Key\":\"Owner\",\"tag3Key\":\"Project\",\"tag4Key\":\"CostCenter\",\"tag5Key\":\"Application\"}"}'
  aws ce update-cost-allocation-tags-status --cost-allocation-tags-status '[{"TagKey":"Environment","Status":"Active"},{"TagKey":"Owner","Status":"Active"},{"TagKey":"Project","Status":"Active"},{"TagKey":"CostCenter","Status":"Active"}]'
```

### Worked example — MANUAL_STEP_REQUIRED, cost allocation activation on legacy account

> Moved to [references/worked-examples.md](references/worked-examples.md#worked-example--manual_step_required-cost-allocation-activation-on-legacy-account).
> Full MANUAL_STEP_REQUIRED report: legacy payer blocks ce update-cost-allocation-tags-status; Billing-console path + 24h propagation.

## Anti-Patterns — NEVER do these things

- NEVER publish a TagPolicy without `enforced_for`. The policy with
  `allowed_values` but no `enforced_for` is advisory — AWS does not
  block non-compliant operations. Operators assume enforcement and
  drift accumulates silently.

- NEVER assume tag policy child policies can override the parent. They
  cannot. Child OU and account policies are additive (union). To relax
  a parent's `allowed_values`, edit the parent. A common mistake is
  attaching a child policy with `allowed_values: ["staging"]` and
  assuming it merges with the parent's `["dev", "prod"]` — it does
  not. The child can only further restrict.

- NEVER use `StringEquals` for ABAC conditions when the tag policy has
  `case_sensitive: false`. The case-insensitive tag policy allows
  `Prod` and `prod`; the IAM condition matches only `prod`. This
  produces silent under-grants (legitimate access denied) OR
  over-grants (a `Deny` with `StringNotEquals` silently passes). Use
  `StringEqualsIgnoreCase` for ABAC conditions OR enforce
  `case_sensitive: true` in the tag policy.

- NEVER assume cost allocation tags are active by default. They are
  NOT. A fully tagged fleet with zero activated tag keys produces
  zero cost-dimension data in Cost Explorer and CUR. Always verify
  with `ce list-cost-allocation-tags --status Active`.

- NEVER deploy a single Config `required-tags` rule for more than 5
  tag keys. The managed rule silently ignores keys beyond the 5th
  (`tag6Key`...`tag7Key` are not accepted parameters). Deploy multiple
  required-tags rules (e.g., `required-tags-core`, `required-tags-ext`).

- NEVER assume `resourcegroupstaggingapi get-resources` returns global
  results. It is region-scoped. Querying only `us-east-1` misses
  resources in other regions. Iterate over all enabled regions.

- NEVER ignore `FailedResourcesMap` in a `tag-resources` response. A
  non-empty map means some resources were not tagged. The API call
  "succeeded" but the tagging is partial. Log, retry, and alert on
  persistent failures.

- NEVER wire auto-tagging without a tag policy. The Lambda stamps
  tags on creation, but nothing stops a human from modifying them
  afterward. Pair auto-tagging with a TagPolicy that enforces
  `allowed_values` on the same keys.

- NEVER set `Automatic: true` on placeholder-tag remediation (e.g.,
  `Environment: unknown`) without a downstream human-correction queue.
  The placeholder satisfies the Config rule but pollutes ABAC and
  cost reporting. Always flag placeholder remediation as a secondary
  manual step.

- NEVER use `aws:RequestTag` in a policy governing read operations
  (`s3:GetObject`, `ec2:DescribeInstances`). `aws:RequestTag` is only
  present on create / tag API calls. A `Deny` with `aws:RequestTag`
  on a read operation silently never matches.

- NEVER assume IAM principal tags propagate to existing sessions.
  `aws:PrincipalTag` is resolved at session creation. Changing a
  user's `Team` tag does not affect active sessions until they
  re-authenticate. Coordinate tag changes with session refresh.

- NEVER forget that Organizations TagPolicy does NOT enforce on
  AWS-generated tags (`aws:cloudformation:stack-name`,
  `aws:createdBy`). These are system tags. User-defined policies apply
  only to user-supplied keys. If your ABAC depends on `aws:createdBy`,
  there is no enforcement lever — it is always present but read-only.

- NEVER deploy ABAC without tagging the IAM principals first. An ABAC
  policy using `aws:PrincipalTag/Team` on an untagged role silently
  denies all access (empty string does not match). Verify principal
  tags with `iam list-user-tags` / `list-role-tags` before deploying
  the policy.

- NEVER bulk-tag resources across accounts without assuming a role in
  each target account. The Tagging API operates within the caller's
  account. A cross-account bulk-tag script requires `sts:AssumeRole`
  into each member account.

## Pre-flight safety checks (run before applying any tag governance CLI)

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#pre-flight-safety-checks-run-before-applying-any-tag-governance-cli).
> Gates: CONFIRM prompt, back up the tag policy (no version history), sandbox-OU test before root, payer API support check, inventory principal tags before ABAC.

## Appendix A — Canonical tag key reference

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#appendix-a--canonical-tag-key-reference).
> 12-row canonical key table: required (Environment/Owner/Project/CostCenter/Application/Team), optional (Backup:Required/ComplianceTier/DataClassification), auto (CreatedAt/CreatorARN/CreatedVia) with consumers.

## Appendix B — Decision tree (which enforcement layer)

```
Is the requirement to PREVENT non-compliant tags at creation?
├─ Yes → Organizations TagPolicy with enforced_for (Step 2)
│         (blocks the API call; does not fix existing resources)
│
└─ No → Is the requirement to DETECT and REPORT missing tags?
        ├─ Yes → Config required-tags rule (Step 5) + Security Hub (Step 6)
        │
        └─ No → Is the requirement to AUTO-STAMP tags on creation?
                ├─ Yes → EventBridge + Lambda auto-tagger (Step 3)
                │
                └─ No → Is the requirement to REMEDIATE existing untagged resources?
                        ├─ Yes → Config → SSM Automation / Lambda remediation (Step 7)
                        │
                        └─ No → Is the requirement to USE tags for access decisions?
                                ├─ Yes → ABAC IAM policy (Step 9)
                                │
                                └─ No → Is the requirement for COST REPORTING?
                                        ├─ Yes → Cost allocation tag activation (Step 8)
                                        │
                                        └─ Default: tag strategy framework (Step 1)
```

## Recent AWS features (2024-2026)

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#recent-aws-features-2024-2026).
> TagPolicy ABAC integration, ce update-cost-allocation-tags-status GA, Tagging API pagination lifts, multi required-tags rules, custom Security Hub findings, EventBridge cross-account routing, STS session tagging.

## Expert heuristic: tag governance blast radius

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic-tag-governance-blast-radius).
> Non-negotiable: sandbox-OU test before root; includes the why (fleet-wide CreateTags outage), five scoping techniques, the 3-phase DETECT→sandbox-ENFORCE→root-ENFORCE rollout, cost-tag and ABAC blast radius, and BLAST_RADIUS/VALIDATION_PHASE output fields.


## References (load on demand)

- [advanced-patterns](references/advanced-patterns.md) — Step 0 expert knowledge, Step 4 Tagging API bulk ops, Step 5 Config rule, Step 6 Security Hub, Appendix A key reference, Recent AWS features, and the blast-radius expert heuristic moved from SKILL.md
- [worked-examples](references/worked-examples.md) — Step 7 remediation recipes (SSM YAML + wiring + Pattern B), the ABAC policy JSON, and the MANUAL_STEP_REQUIRED worked example moved from SKILL.md
- [diagnostic-commands](references/diagnostic-commands.md) — Step 10 baseline audit commands and the pre-flight safety checks moved from SKILL.md
- [organizations-tag-policies](references/organizations-tag-policies.md) — now also holds the full Step 2 TagPolicy authoring recipe moved from SKILL.md
- [auto-tagging-eventbridge-lambda](references/auto-tagging-eventbridge-lambda.md) — now also holds the full Step 3 EventBridge + Lambda auto-tagging recipe moved from SKILL.md

## Domain

AWS CloudOps / Governance Automation — Tag governance, ABAC, cost
allocation.

## AWS documentation

- **Organizations Tag Policies** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_tag-policies.html
- **Resource Groups Tagging API** — https://docs.aws.amazon.com/resourcegroupstagging/latest/APIReference/overview.html
- **AWS Config required-tags Rule** — https://docs.aws.amazon.com/config/latest/developerguide/required-tags.html
- **ABAC for AWS** — https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction_attribute-based-access-control.html
- **Cost Allocation Tags** — https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-alloc-tags.html
- **Security Hub Foundational Security Best Practices** — https://docs.aws.amazon.com/securityhub/latest/userguide/fsbp-standard.html
