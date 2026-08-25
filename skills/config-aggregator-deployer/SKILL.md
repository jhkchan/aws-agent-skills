---
name: config-aggregator-deployer
description: 'Provisions AWS Config aggregators with correct production defaults: organization aggregator (AWS Organizations delegated administrator), authorized accounts (individual 12-digit account IDs with explicit authorization), aggregator-vs-individual-recorder decision, cross-region and cross-account visibility, conformance pack deployment at organization level, organization config rules, Lambda-based config rule processors, and proactive resource evaluation via StartResourceEvaluation. Emits a READY_TO_DEPLOY checklist. Use when creating a Config aggregator, enabling AWS Config across an organization, setting up delegated admin for Config, deploying conformance packs org-wide, authorizing source accounts, configuring multi-account compliance visibility, or enabling proactive compliance checks. Triggers: create Config aggregator, organization aggregator, authorized accounts aggregation, conformance pack, delegated administrator, AWS Config multi-account, proactive rules, Lambda processor config rules.'
license: Apache-2.0
compatibility: 'Requires an LLM agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with configservice, organizations, sts, lambda, iam, and s3 access. Works with Terraform aws_config_configuration_aggregator / aws_config_conformance_pack / aws_config_organization_custom_rule resources, CloudFormation AWS::Config::ConfigurationAggregator / AWS::Config::ConformancePack / AWS::Config::OrganizationConformancePack, and SAM templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Governance
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, config, config-aggregator, governance, compliance, cloudops, deploy, conformance-pack, organizations
  dependencies: aws-orchestrator
  keywords: aws, config, aws-config, config-aggregator, governance, compliance, cloudops, deploy, provisioning, organizations, conformance-pack, organization-config-rule, delegated-administrator, proactive-rules
  when_to_use: Invoke when the user wants to create a new AWS Config aggregator (organization or authorized-account), enable Config across an AWS Organization via delegated administrator, deploy conformance packs at the organization level, set up organization config rules, authorize individual source accounts for aggregation, configure cross-region/cross-account compliance visibility, or enable proactive resource evaluation. Do NOT invoke for individual account Config recorder setup without aggregation — use config-rule-deployer for single-account Config rules.
---

# Config Aggregator Deployer

An AWS CloudOps agent skill that provisions AWS Config
aggregators with correct production defaults. The skill walks the
operator through a 9-step provisioning procedure covering
organization aggregators, authorized accounts, conformance packs,
and proactive rules — explaining why each default matters and
emitting a READY_TO_DEPLOY checklist verifying every configuration
item.

## Quick navigation

| Need | Section |
|---|---|
| What MUST be in the response | "STRICT output contract" |
| Why the aggregation topology matters | "Reasoning framework" |
| What to verify before provisioning | "Prerequisites" |
| The ordered provisioning steps | "Deployment procedure" |
| Common silent-failure pitfalls | "NEVER" |
| Choosing aggregator type, auth model | "Expert heuristic" |
| Aggregation topology matrix | "Topology matrix" |
| 2024-2026 feature changes | "Recent AWS features" |
| Deep CLI sequences | `references/deployment-cli-commands.md` |
| Conformance packs, proactive rules, Lambda | `references/conformance-packs-and-proactive-rules.md` |

## Activation keywords

create Config aggregator, organization aggregator,
AWS Config delegated administrator, authorized accounts
aggregation, individual account aggregation, conformance
pack organization, organization config rule, proactive
config rules, Lambda processor config rule, cross-region
Config visibility, Config multi-account compliance,
StartResourceEvaluation, PutConfigRule proactive mode,
PutAggregationAuthorization, DescribeConfigurationAggregators,
organization conformance pack, deploy AWS Config aggregator,
Config aggregator vs recorder.

## STRICT output contract

When this skill is invoked with a Config aggregator provisioning
request (aggregator name, aggregation type, source accounts or
organization, conformance packs, or a partial existing
configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in "Output format" using the literal all-caps
labels `AGGREGATOR:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of
the response.

### Required output structure

1. `AGGREGATOR: <aggregator-name>` — the Config aggregator being
   provisioned.
2. `VERDICT: READY_TO_DEPLOY` OR `VERDICT: PREREQUISITES_MISSING` —
   nothing else.
3. `CHECKLIST:` followed by indented lines, each prefixed with a
   status marker (`[✓]`, `[✗]`, `[OPTIONAL]`, `[INPUT NEEDED]`).
4. `VERIFICATION_COMMANDS:` followed by indented `aws configservice ...`
   commands the operator can run.

### 6 FORBIDDEN output patterns (each silently breaks automation)

1. **FORBIDDEN — prose preamble before `AGGREGATOR:`.** The first
   non-empty line MUST be `AGGREGATOR:`. No "Here is your
   checklist…".
2. **FORBIDDEN — markdown variants of the labels.** Write
   `VERDICT:`, not `**VERDICT:**`, `### Verdict`, `Verdict =`, or
   `\`VERDICT\``. The labels are case-sensitive all-caps keywords.
3. **FORBIDDEN — swapping verdict tokens.** The verdict is exactly
   `READY_TO_DEPLOY` or `PREREQUISITES_MISSING` — not "ready",
   "missing", "BLOCKED", "OK", or "needs review".
4. **FORBIDDEN — omitting `VERIFICATION_COMMANDS:`.** Even when
   the verdict is `PREREQUISITES_MISSING`, include the commands
   the operator needs to verify the gaps.
5. **FORBIDDEN — extra sections after `VERIFICATION_COMMANDS:`.**
   The checklist block is the entire response. Put deeper
   explanation in `references/` files, not after the block.
6. **FORBIDDEN — status marker drift.** Use only `[✓]`, `[✗]`,
   `[OPTIONAL]`, `[INPUT NEEDED]`. Do not invent `[?]`, `[!]`,
   `[WARN]`, or emoji markers.

### Perfect example (copy the shape exactly)

```text
AGGREGATOR: org-compliance-aggregator
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Aggregator type — OrganizationAggregationSource (OrganizationID: o-abc123def)
  [✓]      Delegated administrator — 123456789012 (Config enabled, all features)
  [✓]      Aggregator region — us-east-1
  [✓]      Source accounts — all accounts in Organization o-abc123def (auto-discovered)
  [✓]      Source regions — all enabled regions
  [✓]      Recorder — config recorder running on delegated admin (recording all resourceTypes)
  [✓]      Delivery channel — S3 bucket config-bucket-123456789012 (Config enabled)
  [✓]      Conformance packs — OperationalBestPractices-for-CloudWatch (deployed org-wide)
  [✓]      Organization config rules — tag-policy-compliance (Lambda processor, ACTIVE)
  [✓]      Proactive rules — s3-bucket-versioning-enabled (Proactive mode via StartResourceEvaluation)
  [✓]      IAM permissions — ConfigRole with AWS_ConfigRole managed policy
  [✓]      Tags — Environment=production, Governance=compliance
  [OPTIONAL] Aggregation authorization — not needed (organization aggregator auto-authorizes)
VERIFICATION_COMMANDS:
  aws configservice describe-configuration-aggregators --configuration-aggregator-names org-compliance-aggregator --region us-east-1
  aws configservice describe-configuration-aggregator-sources-status --configuration-aggregator-name org-compliance-aggregator --region us-east-1
  aws configservice describe-conformance-packs --region us-east-1
  aws configservice describe-organization-conformance-packs --region us-east-1
  aws configservice describe-config-rules --region us-east-1
```

## Reasoning framework (why the aggregation topology matters)

AWS Config aggregation has **topology, authorization, and ordering
constraints** that make the procedure non-trivial:

1. **Organization aggregator FIRST — single pane for all
   accounts.** An organization aggregator pulls Config data from
   every account in the AWS Organization into one aggregator
   account (the delegated administrator). This eliminates
   per-account authorization (PutAggregationAuthorization) and
   auto-discovers new accounts. Requires Organizations "all
   features" enabled and a delegated administrator for Config.

2. **Authorized accounts — manual, for non-Org environments.** If
   the accounts are NOT in an Organization (or only some should be
   aggregated), the aggregator account must call
   `PutAggregationAuthorization` granting the aggregator account
   permission, AND the aggregator must list each account ID +
   region explicitly. This is labor-intensive and error-prone for
   large fleets.

3. **Aggregator vs individual recorder — they serve different
   purposes.** The Config recorder runs in EACH source account and
   records configuration changes to a delivery channel (S3 + SNS).
   The aggregator collects data FROM the recorders across accounts
   and regions into a single view. You MUST have recorders running
   in source accounts for the aggregator to have data — the
   aggregator does NOT record; it aggregates.

4. **Delegated administrator — the right way to enable Config
   org-wide.** Instead of logging into each account and enabling
   Config, designate a delegated administrator. The delegated admin
   account can deploy organization conformance packs and
   organization config rules that apply to ALL accounts
   automatically. New accounts inherit the rules on creation.

5. **Conformance packs at org level — deploy once, apply
   everywhere.** Organization conformance packs deploy a set of
   Config rules and remediation actions to every account in the
   Organization. Deploy from the delegated admin or management
   account. Individual (account-level) conformance packs override
   org-level packs if they share a name.

6. **Proactive rules — check BEFORE deployment.** Proactive Config
   rules evaluate resources before they are created (via
   `StartResourceEvaluation`). This shifts compliance left —
   CloudFormation, CDK, and Terraform can check resources against
   proactive rules during deployment, preventing non-compliant
   resources from ever being created.

7. **Lambda processor rules — custom logic.** Config rules can
   use a Lambda function as the evaluation engine. The Lambda
   receives a configuration-changed event, evaluates the resource
   configuration, and returns compliant/non-compliant verdicts.
   Organization config rules with Lambda processors apply the
   custom rule across all accounts.

## Prerequisites (verify before deployment)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| **Aggregation type decision** | Organization aggregator requires AWS Organizations. Authorized-account requires explicit 12-digit account IDs. The type determines the rest of the configuration. | Confirm whether accounts are in an Organization |
| **Organization ID (for org aggregator)** | The `OrganizationAggregationSource` requires the `RoleArn` and `OrganizationID` (or `AllAwsRegions`). | `aws organizations describe-organization` |
| **Delegated administrator** | The aggregator account must be designated as delegated admin for Config in Organizations. Management account calls `EnableAwsServiceAccess` + `RegisterDelegatedAdministrator`. | `aws organizations list-delegated-administrators --service-principal config.amazonaws.com` |
| **Config enabled in source accounts** | The aggregator can only aggregate data from accounts where Config is enabled (recorder is running). Org aggregator can auto-enable Config in member accounts. | `aws configservice describe-configuration-recorder-status` (per account) |
| **S3 delivery channel** | Each source account writes Config snapshots and history to S3. The delivery channel must be configured with a bucket and (optionally) an SNS topic. | `aws configservice describe-delivery-channels` |
| **IAM role (ConfigRole)** | Each source account needs an IAM role with `AWS_ConfigRole` managed policy and a trust policy allowing `config.amazonaws.com`. | `aws iam get-role --role-name AWS-ConfigRole` |
| **Conformance pack template** | Conformance packs are defined in YAML or JSON templates (sample templates available from AWS). | `aws configservice describe-conformance-pack-templates` |
| **IAM permissions** | Caller needs `configservice:PutConfigurationAggregator`, `configservice:PutAggregationAuthorization`, `configservice:PutConformancePack`, `configservice:PutOrganizationConformancePack`, `organizations:EnableAWSServiceAccess`, `organizations:RegisterDelegatedAdministrator`. | `aws sts get-caller-identity` |

## Deployment procedure (apply in order)

### Step 1: Aggregation type selection (Organization vs Authorized)

| Type | Region | Source model | When to use |
|---|---|---|---|
| `OrganizationAggregationSource` | Aggregator account region | All accounts in AWS Organization (auto-discovered) | Accounts are in an Organization with "all features" enabled. |
| `AccountAggregationSource` | Aggregator account region | Explicit list of 12-digit account IDs + regions | Accounts are NOT in an Organization, or only specific accounts should be aggregated. |

**Decision rule:** use organization aggregation if and only if the
accounts are in an AWS Organization with all features enabled.
Otherwise use authorized-account aggregation.

### Step 2: Delegated administrator setup (organization only)

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

### Step 3: Create the aggregator

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

### Step 4: Authorize source accounts (authorized-account only)

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

### Step 5: Verify recorders in source accounts

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

### Step 6: Conformance packs at organization level

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

### Step 7: Organization config rules with Lambda processor

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

### Step 8: Proactive rules (pre-deployment evaluation)

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

### Step 9: Verification and post-deployment checks

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

## Topology matrix

| Topology | Aggregator type | Auth model | Source accounts | Conformance packs | When to use |
|---|---|---|---|---|---|
| Enterprise (all accounts in Org) | OrganizationAggregationSource | Delegated admin (auto-authorize) | All accounts in Organization | Organization conformance packs | Accounts are in an AWS Organization with all features enabled. |
| Multi-account (not in Org) | AccountAggregationSource | PutAggregationAuthorization (per account) | Explicit list of account IDs | Individual conformance packs per account | Accounts are standalone or in different Organizations. |
| Hybrid (Org + external) | OrganizationAggregationSource + AccountAggregationSource | Delegated admin + per-account auth | Org accounts + explicit external accounts | Org packs for members, individual for externals | Primary fleet in Org, plus a few external partner accounts. |
| Single-region enterprise | OrganizationAggregationSource | Delegated admin | All accounts, specific regions only | Organization conformance packs | Organization spans multiple Regions but compliance is centralized. |

## Visibility: aggregator vs individual recorder

| Aspect | Config recorder (per account) | Config aggregator (central) |
|---|---|---|
| **Purpose** | Records configuration changes for resources in ONE account | Collects data from multiple accounts/regions into ONE view |
| **Scope** | Single account, single region | Multiple accounts, multiple regions |
| **Data stored** | S3 bucket (delivery channel) | Queried via aggregator APIs (not stored separately) |
| **Setup** | `put-configuration-recorder` + `put-delivery-channel` | `put-configuration-aggregator` |
| **Compliance queries** | `get-compliance-details-by-config-rule` (single account) | `get-aggregate-compliance-details-by-config-rule` (cross-account) |
| **Required for aggregator?** | YES — aggregator pulls FROM recorders | N/A |

The aggregator depends on recorders running in source accounts.
Without recorders, the aggregator returns empty results — it does
not record, it aggregates.

## Recent AWS features (2024-2026)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## NEVER (anti-patterns)

- NEVER create an organization aggregator without first enabling
  AWS Config as a trusted service in Organizations
  (`enable-aws-service-access --service-principal
  config.amazonaws.com`). The aggregator creation silently fails
  or shows no source accounts.

- NEVER assume Config recorders are running in source accounts.
  The aggregator collects FROM recorders — if a source account's
  recorder is stopped, the aggregator shows empty data for that
  account with no error. Always verify recorder status with
  `describe-configuration-recorder-status` on source accounts.

- NEVER deploy conformance packs at the individual account level
  when an organization conformance pack already covers those
  accounts. Individual packs override org-level packs of the same
  name, creating inconsistent compliance across accounts.

- NEVER create an authorized-account aggregator without calling
  `PutAggregationAuthorization` on each source account. The
  aggregator will list the accounts but the source status will
  show "FAILED" — data never arrives. Organization aggregators
  skip this step because the delegated admin auto-authorizes.

- NEVER confuse the aggregator RoleArn (management account role
  for reading org membership) with the source account ConfigRole
  (per-account role for recording). They are different roles in
  different accounts. The aggregator RoleArn needs
  `organizations:ListAccounts`; the ConfigRole needs
  `AWS_ConfigRole` managed policy.

- NEVER omit the delivery channel (S3 bucket) on source accounts.
  Without a delivery channel, the recorder runs but does not
  persist configuration snapshots or history — the aggregator
  gets partial data.

- NEVER deploy a Lambda processor organization config rule
  without granting Config permission to invoke the Lambda
  (`lambda:InvokeFunction` in the Lambda resource policy with
  `config.amazonaws.com` principal). Without this, evaluations
  silently fail.

- NEVER deviate from the checklist output format. Substituting
  `Verdict` / `**VERDICT**` / `### Verdict:` for the literal
  `VERDICT:` label silently breaks downstream deployment pipelines
  and assertion-based evals.

## Expert heuristic — choosing aggregator type and auth model

**Organization vs authorized-account:** if the accounts are in an
AWS Organization with all features enabled, ALWAYS use an
organization aggregator. It auto-discovers accounts, auto-enables
Config in member accounts, and requires no per-account
authorization. Use authorized-account aggregation only when
accounts are standalone or in different Organizations.

**Delegated administrator — the right pattern:** designate one
account (typically a logging or security account) as the
delegated administrator for Config. This account becomes the
aggregation hub and can deploy org-wide conformance packs and
config rules. New accounts auto-inherit compliance rules on
creation.

**Conformance packs — org-level by default:** deploy conformance
packs at the organization level from the delegated admin. This
ensures consistent compliance across all accounts. Reserve
individual account conformance packs for exceptions or overrides.

**Proactive rules — shift compliance left:** enable proactive mode
on critical rules (e.g., S3 public access, security group rules,
IAM policies). Integrate `StartResourceEvaluation` into CI/CD
pipelines so non-compliant resources are blocked before creation.
This is cheaper than remediating after deployment.

**Lambda processor rules — for custom logic:** use a Lambda-backed
Config rule when no managed rule covers your compliance check
(e.g., custom naming conventions, tag schemas, multi-resource
relationships). Deploy as an organization config rule so it
applies everywhere. Start with a Lambda running in the delegated
admin account and an org rule referencing it.

**Recording scope — all resource types vs specific:** by default,
Config records all supported resource types. For cost-sensitive
environments, configure the recorder to record only specific
resource types. The aggregator inherits whatever scope the
source account recorders use — a narrower recorder scope means
narrower aggregation visibility.

## Pre-flight safety checks (run before any provisioning CLI)

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).

## Output format — MANDATORY literal labels

When invoked with a Config aggregator provisioning request, your
ENTIRE response MUST be the checklist block below. The labels are
**case-sensitive all-caps keywords** — write them EXACTLY as
shown. Do NOT write a preamble. Start with `AGGREGATOR:` and stop
after the `VERIFICATION_COMMANDS:` block.

```text
AGGREGATOR: <aggregator-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓]      Aggregator type — <OrganizationAggregationSource | AccountAggregationSource>
  [✓]      Delegated administrator — <account-id> (Config enabled, all features)
  [✓]      Aggregator region — <region>
  [✓]      Source accounts — <all accounts in Org o-xxx | explicit account list>
  [✓]      Source regions — <all regions | specific regions>
  [✓]      Recorder — <running on delegated admin | status per source account>
  [✓]      Delivery channel — <S3 bucket name | not configured>
  [✓]      Conformance packs — <pack names | none>
  [✓]      Organization config rules — <rule names | none>
  [✓]      Proactive rules — <rule names | none>
  [✓]      IAM permissions — <ConfigRole + aggregator role status>
  [✓]      Tags — <key=value pairs>
  [OPTIONAL] Aggregation authorization — <needed for authorized-account | not needed for org>
VERIFICATION_COMMANDS:
  aws configservice describe-configuration-aggregators --configuration-aggregator-names <aggregator-name> --region <region>
  aws configservice describe-configuration-aggregator-sources-status --configuration-aggregator-name <aggregator-name> --region <region>
  aws configservice describe-organization-conformance-packs --region <region>
  aws configservice describe-config-rules --region <region>
```

**Status marker semantics:**
- `[✓]` — configuration is applied and verified.
- `[✗]` — configuration is NOT applied or is misconfigured. Cite
  the gap.
- `[OPTIONAL]` — recommended but not required for the topology
  type.
- `[INPUT NEEDED]` — a prerequisite value is missing (Organization
  ID, account IDs, S3 bucket, conformance pack template) and the
  operator must provide it before provisioning can proceed.

**PREREQUISITES_MISSING verdict:** if any REQUIRED prerequisite is
missing (Organization ID for org aggregator, account IDs for
authorized-account aggregator, delegated admin not configured,
Config not enabled in source accounts, delivery channel missing),
the verdict is `PREREQUISITES_MISSING` with each gap listed. The
checklist shows the target configuration with `[INPUT NEEDED]`
or `[✗]` for unmet prerequisites.

## Edge-case handling

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — deployment Steps 2-9 CLI walkthroughs moved from SKILL.md
- [references/advanced-patterns.md](references/advanced-patterns.md) — 2024-2026 feature changes + edge-case handling moved from SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-provisioning safety checks moved from SKILL.md
- [references/deployment-cli-commands.md](references/deployment-cli-commands.md) — full copy-pasteable CLI sequences for all 9 steps + Terraform/CloudFormation equivalents
- [references/conformance-packs-and-proactive-rules.md](references/conformance-packs-and-proactive-rules.md) — conformance packs, proactive rules, Lambda processors, multi-account compliance queries

## Domain

AWS CloudOps / AWS Config Aggregation and Governance Provisioning.

## AWS documentation

- **AWS Config Developer Guide** — https://docs.aws.amazon.com/config/latest/developerguide/
- **Config Aggregators** — https://docs.aws.amazon.com/config/latest/developerguide/aggregate-data.html
- **Organization Aggregator** — https://docs.aws.amazon.com/config/latest/developerguide/organization-aggregator.html
- **Authorized Account Aggregation** — https://docs.aws.amazon.com/config/latest/developerguide/authorize-aggregator-account.html
- **Conformance Packs** — https://docs.aws.amazon.com/config/latest/developerguide/conformance-packs.html
- **Organization Conformance Packs** — https://docs.aws.amazon.com/config/latest/developerguide/org-conformance-packs.html
- **Proactive Rules** — https://docs.aws.amazon.com/config/latest/developerguide/proactive-rules.html
- **Config Managed Rules** — https://docs.aws.amazon.com/config/latest/developerguide/managed-rules-by-aws-config.html
- **Config CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/configservice/

## References

- `references/deployment-cli-commands.md` — full copy-pasteable CLI
  command sequence for all 9 provisioning steps, including
  delegated admin setup, organization and authorized-account
  aggregator creation, aggregation authorization, recorder
  verification, conformance pack deployment, organization config
  rules with Lambda processors, proactive rule configuration, and
  Terraform `aws_config_configuration_aggregator` /
  `aws_config_conformance_pack` /
  `aws_config_organization_conformance_pack` /
  `aws_config_organization_custom_rule` resource equivalents.

- `references/conformance-packs-and-proactive-rules.md` — deep
  reference on conformance pack templates (AWS sample packs, custom
  templates, org vs account scope, override behavior), proactive
  rule evaluation lifecycle (`StartResourceEvaluation` →
  `GetResourceEvaluationStatus`), Lambda processor rule patterns
  (event schema, evaluation API, `put_evaluations`), and
  multi-account compliance query patterns via aggregator APIs.
