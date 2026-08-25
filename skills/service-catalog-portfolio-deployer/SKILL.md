---
name: service-catalog-portfolio-deployer
description: 'Provisions AWS Service Catalog portfolios and products with production-safe defaults: portfolio creation (DisplayName, ProviderName, description), product creation from CloudFormation templates (CLOUDFORMATION_TEMPLATE, semantic versions, provisioning artifacts), constraints (LAUNCH stack/template-based roles, STACK_UPDATE, TAG_UPDATE, NOTIFICATION), launch paths (local + shared via Organizations), portfolio sharing (org, account, OU), TagOptions (key-value pairs applied to launched products), and latest primitives (Terraform Open Source, Service App Registry, Terraform Cloud). Emits READY_TO_DEPLOY / PREREQUISITES_MISSING with verified portfolios, products, constraints, and copy-pasteable servicecatalog + iam + sns commands. Use when provisioning Service Catalog for self-service launchpad, governance-gated distribution, or cross-account template distribution. Triggers: Service Catalog, portfolio, product, launch constraint, TagOptions, organizational sharing, self-service launchpad.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Live provisioning uses AWS CLI v2 with servicecatalog (create-portfolio, create-product, create-constraint, associate-product-with-portfolio, create-portfolio-share, create-tag-option, associate-tag-option-with-resource), cloudformation (validate-template), iam (create-role, pass-role), sns (create-topic), and organizations (enable-aws-service-access, list-delegated-administrators). Works with Terraform...
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
  when_to_use: Provisioning a Service Catalog portfolio for self-service product distribution; creating a product from a CloudFormation template; applying constraints (launch role, tag update, stack update, notification); configuring launch paths for a local account or sharing a portfolio via AWS Organizations; setting up TagOptions for governed tag application; integrating Service Catalog with Service App Registry for application inventory tagging; or provisioning Service Catalog with Terraform Open Source. Do NOT invoke for launching a product instance (use the appropriate operate skill), for AWS Marketplace integration (separate workflow), or for non-Service-Catalog CloudFormation deployment.
  activation_triggers: Service Catalog portfolio, Service Catalog product, launch constraint, stack-based constraint, template-based constraint, tag-update constraint, notification constraint, launch path, portfolio share, organizational sharing, TagOptions, self-service launchpad, CloudFormation product, product versioning, Service App Registry, Service Catalog Terraform
  invocation_schema: 'Input: either (a) a portfolio spec including DisplayName, ProviderName, products (name + CloudFormation URL + version), constraints, launch paths, TagOptions, and sharing target; or (b) a partial spec for interactive refinement (e.g., "Service Catalog portfolio with a curated S3-bucket product and a launch role"). Output: a deterministic PORTFOLIO / VERDICT / CHECKLIST / VERIFICATION_COMMANDS block per the STRICT output contract, where VERDICT is READY_TO_DEPLOY or PREREQUISITES_MISSING.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: aws, service catalog, portfolio, product, provisioning artifact, launch constraint, stack-based constraint, template-based constraint, tag-update constraint, notification constraint, launch path, portfolio share, organizational sharing, tagoptions, self-service launchpad, cloudformation product, product versioning, service app registry, cloudops, deploy
  tags: aws, service-catalog, portfolio, product, launch-constraint, tagoptions, governance, deploy
  dependencies: aws-orchestrator
---

# Service Catalog Portfolio Deployer

## What this skill does

Provisions AWS Service Catalog portfolios and products with correct
production-safe defaults: a least-privilege launch role passed via the
LAUNCH constraint, scoped launch paths, portfolio sharing (account-
level or organization-level), TagOptions for governed tag application,
and versioned provisioning artifacts. The skill walks an 8-step
procedure, surfaces the silent-failure modes unique to Service Catalog
(most dangerous: a product launched without a LAUNCH constraint
deploys as the end-user's permissions — a privilege-escalation path
that produces production resources owned by individual operators), and
emits a READY_TO_DEPLOY checklist verifying every portfolio, product,
constraint, and share against the IAM and Organizations state. The
single most common incident this skill prevents: an administrator
publishes a powerful product (e.g., VPC creator) to a portfolio shared
with the whole organization, with no LAUNCH constraint, and any user
with launch permissions deploys a full VPC in any account using their
own broad role — runaway cost and compliance drift with no central
governance.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Provisioning summary (8 steps), verdict thresholds, constraint matrix | Before any operation |
| **Activation keywords** | Phrases that route to this skill | Disambiguating routing |
| **Invocation contract** | Required literal labels in the response | Formatting the response |
| **Reasoning framework** | Why the 8-step order matters; launch-permission model | Understanding the deploy model |
| **Dependency graph** | Which configs silently no-op without their prerequisite | Debugging "product not visible / can't launch" |
| **Expert heuristic** | Launch-constraint myth; share-region quirk; TagOptions inheritance | Pre-empt production incidents |
| **Prerequisites** | What to verify before emitting any command | Avoid PREREQUISITES_MISSING rework |
| **8-step procedure** | The actual provisioning with copy-pasteable CLI | Executing the deploy |
| **NEVER (top 5)** | Hard rules that prevent privilege escalation / governance gaps | Review before deploy |
| **STRICT output contract** | Required PORTFOLIO / VERDICT / CHECKLIST / VERIFICATION_COMMANDS block | Formatting the response |
| **Recent AWS features** | Terraform Open Source, App Registry, CloudFormation StackSets | Stay current |

## Quick reference — provisioning summary (8 steps)

| Step | Action | Reversible? | Key risk if skipped |
|---|---|---|---|
| 1 | Confirm portfolio intent + consumer scope | — | wrong scope = wrong visibility |
| 2 | Create portfolio (DisplayName, ProviderName, description) | Yes | missing description = unsearchable |
| 3 | Create products + provisioning artifacts (versions) | Yes | wrong template URL = launch failure |
| 4 | Associate products with the portfolio | Yes | unassociated product = invisible |
| 5 | Configure constraints (LAUNCH, TAG_UPDATE, STACK_UPDATE, NOTIFICATION) | Yes | no LAUNCH = end-user deploys as themselves |
| 6 | Configure TagOptions + bind to portfolio/products | Yes | no TagOptions = ungoverned tagging |
| 7 | Configure launch paths + portfolio shares (account, OU, org) | Yes | wrong share target = governance gap |
| 8 | Verify via `search-products` + `describe-portfolio` + emit checklist | — | silent no-ops |

**Critical ordering constraints:** portfolio exists before products
(products need a parent association); products created with their
initial provisioning artifact before constraints (constraints
reference product IDs); launch role created before the LAUNCH
constraint (the constraint references `RoleArn`); TagOptions bound
before sharing (so consumers inherit tag policy on launch); shares
configured last (sharing an unconstrained portfolio exposes the
governance gap immediately). Rationale and the silent-failure table
are below.

## Activation keywords

Service Catalog portfolio, Service Catalog product, provisioning
artifact, product version, launch constraint, stack-based constraint,
template-based constraint, tag-update constraint, notification
constraint, launch path, portfolio share, organizational sharing,
TagOptions, self-service launchpad, CloudFormation product, Service
App Registry, Service Catalog Terraform, delegated administrator.

## Invocation contract (hard requirement)

When this skill is invoked with a Service Catalog portfolio
provisioning request, the agent MUST respond with the checklist
defined in §"STRICT output contract" using the literal all-caps labels
`PORTFOLIO:`, `VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`.
Do NOT preface with prose, headings, or disclaimers — emit the block
as the first lines of the response. This contract is what assertion-
based evals and downstream provisioning pipelines rely on; deviating
from the literal labels breaks automation silently.

## Reasoning framework (why the provisioning order matters)

Service Catalog looks like "publish a portfolio of templates" but the
underlying model has four traps:

1. **The LAUNCH constraint determines the role that provisions the
   product — not the launching user's role.** Without a LAUNCH
   constraint, CloudFormation deploys using the launching user's
   permissions. That means an operator with broad IAM can launch a
   VPC, an IAM role, a Lambda — anything their role allows — and the
   resource belongs to them, not the central governance team. The
   LAUNCH constraint pins the provisioning to a specific role
   (typically a role with only the product's required permissions),
   regardless of who launches it. This is the central governance
   primitive of Service Catalog.

2. **Two constraint scoping models exist: STACK-based and TEMPLATE-
   based.** A STACK-based launch constraint passes the same role for
   every launch of the product. A TEMPLATE-based launch constraint
   applies a rules engine to choose the role per-launch (e.g., based
   on the launching user's team). Template-based constraints are
   powerful but rarely used; the canonical pattern is STACK-based with
   one role per product family. Mixing them silently degrades to
   STACK-based when the template engine produces no match.

3. **Portfolio shares are region-scoped.** Sharing a portfolio with an
   Organization account does NOT make the portfolio visible in other
   regions. A share in us-east-1 is invisible to a user in eu-west-1
   unless they switch regions in the console. For multi-region
   deployments, replicate the portfolio per region or document the
   region expectation explicitly.

4. **TagOptions are NOT Service Control Policies.** TagOptions are a
   "suggested tags" mechanism: when a user launches a product
   associated with a TagOption, the tag is pre-populated in the launch
   wizard. The user can change the value or remove the tag entirely
   (unless TAG_UPDATE constraint is set to `NOT_ALLOWED`). TagOptions
   do not enforce tagging; they suggest it. Enforce tagging via SCP
   on the organization or via a CloudFormation-backed tag policy.

The procedure below sequences the steps to surface these traps.

## Dependency graph (silent-failure table)

| Configuration | Hard dependencies (API error without) | Silent failure mode (returns 200, does nothing useful) | Enables downstream |
|---|---|---|---|
| Portfolio | unique DisplayName | **portfolio with same DisplayName in different accounts creates duplicate invisible inventories** | container for products |
| Product (CLOUDFORMATION_TEMPLATE) | valid CloudFormation URL | **product with broken template URL launches OK, fails at stack create with no alarm** | launchable item |
| Provisioning artifact (version) | semantic version string | **two artifacts with same version silently overwrites "active" flag; old version invisible** | versioned launches |
| Product-portfolio association | product ID + portfolio ID | **unassociated product silently invisible to portfolio users** | product visibility |
| LAUNCH constraint (STACK-based) | valid RoleArn (PassRole) | **no LAUNCH constraint = CloudFormation deploys as the end-user's role = privilege escalation risk** | governance |
| LAUNCH constraint (TEMPLATE-based) | template rules engine | **template rule that matches no role silently degrades to no constraint = end-user role** | conditional governance |
| TAG_UPDATE constraint | product ID | **default allows tag changes post-launch — TagOptions suggested at launch can be removed** | tag immutability |
| NOTIFICATION constraint | SNS ARN | **SNS topic with no subscribers = notifications silently lost** | launch tracking |
| TagOption | unique key+value | **TagOption not associated with portfolio = never applied at launch** | governed tagging |
| Launch path | local account by default | **no launch path in shared account = portfolio visible but unlaunchable** | cross-account launching |
| Portfolio share (account-level) | account ID | **share to wrong account ID = silent invisible; no error, no usage** | cross-account visibility |
| Portfolio share (org-level) | Organizations `servicecatalog:enable` | **share without delegated admin = recipients see portfolio but cannot manage** | centralized catalog |
| Portfolio share (OU-level) | OU ID | **share to OU root vs. OU child silently changes recipient set** | scoped distribution |
| App Registry association | application exists | **application deleted after association = association silently inert** | application inventory |

**The four most dangerous silent-failure rows** are no-LAUNCH-
constraint, TEMPLATE-based-no-match-degradation, region-scoped-share-
visibility, and TagOptions-not-associated. All return success on the
API call; the failure surfaces only when a product is launched
without governance or a user cannot find the portfolio. Step 5
(LAUNCH constraint), Step 7 (sharing with region/delegated-admin
verification), and Step 8 (`search-products` + `describe-portfolio`
as the recipient account) are non-negotiable for any production-
adjacent portfolio.

## Expert heuristic: the no-LAUNCH-constraint myth

The most common misconception: "the launching user's permissions
govern what the product can deploy." They do, by default — and that
is the problem.

```text
Operator thinks:                  What actually happens:
"User launches product; their     Without a LAUNCH constraint,
permissions scope the launch."    CloudFormation assumes the user's
                                  role. A user with PowerUserAccess
                                  launches a VPC product and deploys
                                  a full VPC, NAT gateways, transit
                                  gateway attachments — all owned
                                  by their individual role. Central
                                  governance has no visibility into
                                  the resources until audit time.
```

The LAUNCH constraint is the single most important governance
primitive in Service Catalog. It pins CloudFormation to a specific
role whose permissions match ONLY the product's requirements — not
the launching user's permissions. An admin launches a curated VPC
product; the launch role has only `ec2:*` and `iam:PassRole`; the
admin cannot inject a privilege-escalation role via a template
parameter because the launch role will not pass arbitrary roles.

**The remedy is one launch role per product family** (e.g.,
`sc-launch-vpc-role`, `sc-launch-s3-role`), each scoped to only the
permissions that product family requires. Tag conditions on the
launch role add a second line of defense (e.g., the role only passes
roles tagged `sc-launch-approved=true`).

## Expert heuristic: portfolio share region quirk

A portfolio share is region-scoped. The `create-portfolio-share`
call has no region parameter — it uses the region of the calling
profile. A share to organization `o-abc123` made from a us-east-1
caller makes the portfolio visible to users in us-east-1 only. A user
in eu-west-1 will not see the portfolio in their console unless they
switch regions to us-east-1.

**For multi-region deployments:**
1. Replicate the portfolio in each region via CloudFormation
   StackSets, or
2. Document the region expectation explicitly in the portfolio
   description, or
3. Build a custom launcher (Lambda-backed) that copies the share to
   every region in scope.

The region quirk is silent — no error, the share appears to apply
"everywhere" but only resolves in one region.

## Expert heuristic: TagOptions vs. SCPs vs. TAG_UPDATE constraint

Three independent mechanisms govern tags on Service Catalog-launched
products. Operators frequently conflate them.

- **TagOptions** (suggested): when a user launches a product
  associated with a TagOption, the tag is pre-populated in the launch
  wizard. The user can change the value or remove the tag.
- **TAG_UPDATE constraint (`NOT_ALLOWED`)**: prevents the user from
  modifying the tags on the launched product's CloudFormation stack
  after launch. It does NOT prevent modification at launch time —
  only post-launch.
- **SCP / tag policy on the organization**: enforces tag compliance
  across the entire account, including Service Catalog launches. This
  is the only one of the three that can enforce a tag value at launch
  time.

For true tag governance, use all three: TagOptions to suggest, TAG_
UPDATE constraint to lock post-launch, and SCP to enforce at the
control-plane layer.

## Prerequisites (verify before provisioning)

Before emitting any provisioning command, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING** with a
specific gap citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Caller IAM | `servicecatalog:CreatePortfolio`, `iam:CreateRole`, `iam:PassRole` required | `aws sts get-caller-identity` + IAM policy check |
| CloudFormation template URL resolvable | Broken URL = launch failure at consumer time | `aws cloudformation validate-template --template-url <URL>` |
| Launch role exists (for LAUNCH constraint) | Constraint references RoleArn | `aws iam get-role --role-name <name>` |
| Organizations enabled (for org/OU shares) | Org-level share requires Organizations | `aws organizations describe-organization` |
| Service Catalog delegated admin (for cross-account) | Recipients can view but not manage without it | `aws organizations list-delegated-administrators --service-principal servicecatalog.amazonaws.com` |
| SNS topic exists (for NOTIFICATION constraint) | Constraint references SNS ARN | `aws sns get-topic-attributes --topic-arn <arn>` |
| Tag keys (for TagOptions) | TagOption key must exist before associating | `aws servicecatalog list-tag-options` |
| Region of share matches consumer region | Shares are region-scoped | Caller region matches target user's region |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## 8-step provisioning procedure

### Step 1 — Confirm portfolio intent + consumer scope

Before any resource lookup, name the intent in one sentence:
"distribute a curated S3-bucket product to all organization accounts
for analytics workloads," or "self-service launchpad for the
platform team in this account only." The intent drives the share
target, the launch role scope, and the constraint set.

### Step 2 — Create portfolio

```bash
aws servicecatalog create-portfolio \
  --display-name "Curated S3 Products" \
  --provider-name "Platform Governance" \
  --description "S3-bucket products for analytics workloads. Launch role scoped to s3:* only. Region: us-east-1." \
  --tags Key=Owner,Value=platform-governance
```

The `description` field is searchable in the consumer console —
include the region, the launch-role summary, and the intended consumer
scope. Missing description = consumers cannot find the portfolio.

### Step 3 — Create products + provisioning artifacts

```bash
PRODUCT_ID=$(aws servicecatalog create-product \
  --name "Curated S3 Bucket" \
  --owner "Platform Governance" \
  --product-type CLOUDFORMATION_TEMPLATE \
  --provisioning-artifact-parameters \
    '{"Name":"v1.0.0","Description":"Initial release","Info":{"LoadTemplateFromURL":"https://s3.amazonaws.com/platform-templates-us-east-1/s3-bucket.yaml"},"Type":"CLOUD_FORMATION_TEMPLATE"}' \
  --query 'RecordDetail.ProductId' --output text)
```

For versioned releases, create additional provisioning artifacts on
the same product:

```bash
aws servicecatalog create-provisioning-artifact \
  --product-id $PRODUCT_ID \
  --parameters file://v1-1-0.json
```

A provisioning artifact is a version. Multiple versions can coexist;
consumers pick one at launch. The "active" version is the default;
older versions remain launchable for rollback.

**Common mistake:** using `LoadTemplateFromURL` with a private S3
URL. The URL must be accessible to Service Catalog (presigned or
public-read). A private URL launches OK but fails at stack-create
time with no alarm.

### Step 4 — Associate products with the portfolio

```bash
aws servicecatalog associate-product-with-portfolio \
  --product-id $PRODUCT_ID \
  --portfolio-id $PORTFOLIO_ID
```

A product not associated with any portfolio is silently invisible to
all consumers — even the administrator. Association is what makes the
product available inside the portfolio.

**Common mistake:** creating the product but forgetting the
association. The product appears in `search-products-as-admin` but
not in `search-products` (the consumer-facing API).

### Step 5 — Configure constraints (LAUNCH, TAG_UPDATE, NOTIFICATION)

```bash
# Create the launch role first (Step 5 prereq)
aws iam create-role --role-name sc-launch-s3-role --assume-role-policy-document file://trust-policy.json
aws iam put-role-policy --role-name sc-launch-s3-role --policy-name s3-only --policy-document file://s3-only-policy.json

# Create the LAUNCH constraint
aws servicecatalog create-constraint \
  --portfolio-id $PORTFOLIO_ID \
  --product-id $PRODUCT_ID \
  --parameters '{"RoleArn":"arn:aws:iam::111111111111:role/sc-launch-s3-role","LocalRoleName":"sc-launch-s3-role"}' \
  --type LAUNCH
```

Constraint types:

| Type | Effect | Required? |
|---|---|---|
| `LAUNCH` | CloudFormation assumes the specified role at launch (not the user's role) | YES — without this, end-user permissions apply |
| `TAG_UPDATE` | `NOT_ALLOWED` blocks tag changes to the launched stack post-launch | Recommended |
| `STACK_UPDATE` | `NOT_ALLOWED` blocks updates to the launched stack post-launch (immutable launches) | Optional |
| `NOTIFICATION` | Sends SNS notifications for launch/update/terminate events | Recommended for audits |
| `LAUNCH_PERMISSION` | Limits who can launch the product (via principal ARNs) | Optional |

**Common mistake:** using a `TEMPLATE`-type launch constraint without
testing the rules engine. A template rule that matches no role
silently degrades to no constraint — the end-user's role is used.

### Step 6 — Configure TagOptions + bind to portfolio/products

```bash
TAG_OPTION_ID=$(aws servicecatalog create-tag-option \
  --key "CostCenter" \
  --value "platform-1234" \
  --query 'TagOptionDetail.Id' --output text)

aws servicecatalog associate-tag-option-with-resource \
  --resource-id $PORTFOLIO_ID \
  --tag-option-id $TAG_OPTION_ID
```

Bind TagOptions at the portfolio level (inherited by all products in
the portfolio) or at the product level (product-specific). Portfolio-
level TagOptions propagate to every product on launch.

### Step 7 — Configure launch paths + portfolio shares

**Local account launch path** is implicit — no configuration needed.
The portfolio is launchable by users in the source account (subject
to IAM).

**Cross-account share (account-level):**
```bash
aws servicecatalog create-portfolio-share \
  --portfolio-id $PORTFOLIO_ID \
  --account-id 222222222222
```

**Cross-account share (organization-level):**
```bash
# Enable Service Catalog access in Organizations
aws organizations enable-aws-service-access \
  --service-principal servicecatalog.amazonaws.com

# Share to the entire organization
aws servicecatalog create-portfolio-share \
  --portfolio-id $PORTFOLIO_ID \
  --organization-node Type=ORGANIZATION,Value=o-abc123def456
```

**Cross-account share (OU-level):**
```bash
aws servicecatalog create-portfolio-share \
  --portfolio-id $PORTFOLIO_ID \
  --organization-node Type=ORGANIZATIONAL_UNIT,Value=ou-abc1-abcdef
```

**Common mistake:** sharing to the organization root vs. the
organization ID. `Type=ORGANIZATION` shares to every account in the
org; `Type=ORGANIZATIONAL_UNIT` with the OU root ID shares to a
subset. Confirm the recipient set explicitly.

### Step 8 — Verify via `search-products` + `describe-portfolio`

```bash
# Verify portfolio is stored
aws servicecatalog describe-portfolio --id $PORTFOLIO_ID

# Verify product is associated
aws servicecatalog search-products-as-admin --portfolio-id $PORTFOLIO_ID

# Verify constraints
aws servicecatalog describe-constraint --id <CONSTRAINT_ID>

# Cross-account verification: switch to a consumer profile and search
aws servicecatalog search-products --profile consumer-profile
```

Cross-account verification is critical: a share that looks successful
from the source account may be invisible in the consumer account due
to region mismatch, missing delegated admin, or IAM scoping.

## NEVER do these things

These anti-patterns cause privilege escalation, governance gaps, or
silent no-ops. Each is observed in real production incidents.

1. **NEVER publish a product without a LAUNCH constraint.** Why it's
   wrong: without a LAUNCH constraint, CloudFormation assumes the
   launching user's role. An operator with PowerUserAccess launches a
   powerful product and deploys resources owned by their individual
   role. Central governance has no visibility until audit time. Always
   configure a STACK-based LAUNCH constraint with a least-privilege
   role scoped to the product's required permissions.

2. **NEVER use a TEMPLATE-based LAUNCH constraint without testing the
   rules engine against every consumer path.** Why it's wrong: a
   template rule that matches no role silently degrades to no
   constraint. The end-user's role is used. The remediation is to
   fall back to STACK-based constraints with a default role, and to
   unit-test template rules with every consumer persona before
   deployment.

3. **NEVER share a portfolio at the organization root when you mean
   an OU subset.** Why it's wrong: `Type=ORGANIZATION` shares to every
   account in the org, including Sandbox, Security, and Audit
   accounts. Use `Type=ORGANIZATIONAL_UNIT` with a specific OU ID,
   and document the recipient set in the portfolio description.

4. **NEVER assume a portfolio share is multi-region.** Why it's
   wrong: shares are region-scoped to the caller's region. A share
   from us-east-1 is invisible in eu-west-1. For multi-region
   deployments, replicate the portfolio via CloudFormation StackSets
   or document the region expectation explicitly.

5. **NEVER use TagOptions as the only tag-governance mechanism.** Why
   it's wrong: TagOptions are suggestions, not enforcement. A user
   can remove a suggested tag at launch or post-launch (unless TAG_
   UPDATE constraint is set). For true tag governance, combine
   TagOptions, TAG_UPDATE constraint, and an SCP/tag policy at the
   organization level.

## Output format

```
PORTFOLIO: <display-name> (products: <count>, shares: <recipient-summary>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Intent + consumer scope: <one-sentence intent>, scope <local|account|OU|org>
  [✓|✗] Portfolio created: <display-name> by <ProviderName> (<region>)
  [✓|✗] Product(s): <count> products, <count> provisioning artifacts (versions)
  [✓|✗] Product-portfolio association: <count> associations
  [✓|✗] Constraint(s): LAUNCH <role-name> (STACK-based), TAG_UPDATE <value>, NOTIFICATION <sns-name>
  [✓|✗] TagOptions: <count> key-value pairs bound at portfolio level
  [✓|✗] Share(s): <recipient-summary> (region: <caller-region>, delegated admin: <true|false>)
VERIFICATION_COMMANDS:
  <copy-pasteable verification commands>
```

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
checklist that looks complete but contains a silent misconfiguration.
Self-check EVERY emitted block against these rules before returning.

### Required output structure

Every response MUST be a single block using these literal labels, in
this order. Do NOT preface with prose, headings, or disclaimers.

```text
PORTFOLIO: <display-name> (products: <count>, shares: <recipient-summary>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Intent + consumer scope: <one-sentence intent>, scope <local|account|OU|org>
  [✓|✗] Portfolio created: <display-name> by <ProviderName> (<region>)
  [✓|✗] Product(s): <count> products, <count> provisioning artifacts (versions)
  [✓|✗] Product-portfolio association: <count> associations
  [✓|✗] Constraint(s): LAUNCH <role-name> (STACK-based), TAG_UPDATE <value>, NOTIFICATION <sns-name>
  [✓|✗] TagOptions: <count> key-value pairs bound at portfolio level
  [✓|✗] Share(s): <recipient-summary> (region: <caller-region>, delegated admin: <true|false>)
VERIFICATION_COMMANDS:
  <copy-pasteable verification commands — one per [✓] item>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: READY_TO_DEPLOY` without showing ALL 7
   checklist items.** Every item MUST appear with a status marker:
   `[✓]`, `[✗]`, or `[OPTIONAL]`. Omitting a row implies it was not
   evaluated.

2. **NEVER mark Constraint(s) `[✓] LAUNCH` without citing the role
   name AND confirming it is STACK-based (or TEMPLATE-based with a
   tested default fallback).** A LAUNCH constraint with no role ARN
   silently falls back to the end-user's role — privilege escalation.
   The checklist MUST cite the role name and the constraint scoping
   model.

3. **NEVER mark Share(s) `[✓]` without citing the recipient scope
   (ORGANIZATION, ORGANIZATIONAL_UNIT, ACCOUNT) AND the caller
   region.** Region mismatch is the leading cause of "portfolio
   invisible in consumer account" tickets. The checklist MUST cite
   both.

4. **NEVER mark TagOptions `[✓]` without citing the binding level
   (portfolio vs. product).** Portfolio-level TagOptions propagate to
   every product; product-level TagOptions are scoped. Mixing them
   silently produces inconsistent tagging.

5. **NEVER mark Product(s) `[✓]` without citing the provisioning
   artifact count AND the active version.** A product with one
   provisioning artifact has no rollback; a product with multiple
   untagged artifacts is ambiguous at launch.

6. **NEVER emit `VERDICT: PREREQUISITES_MISSING` without citing the
   specific gap.** Each `[✗]` item MUST have a one-line reason:
   `[✗] Share(s): Organizations not enabled — enable
   enable-aws-service-access for servicecatalog.amazonaws.com before
   sharing`. A bare `[✗]` is non-compliant.

7. **NEVER include `TEMPLATE`-type LAUNCH constraint in the checklist
   without a `[WARN]` note.** Template-based constraints silently
   degrade to no constraint when no rule matches. The checklist MUST
   cite the fallback role or mark the item `[✗]`.

### Perfect example output — READY_TO_DEPLOY

```text
PORTFOLIO: Curated S3 Products (products: 1, shares: ou-abc1-abcdef in us-east-1)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Intent + consumer scope: Distribute a curated S3-bucket product to platform-team OU for analytics workloads, scope OU
  [✓] Portfolio created: Curated S3 Products by Platform Governance (us-east-1)
  [✓] Product(s): 1 product (Curated S3 Bucket), 2 provisioning artifacts (v1.0.0 active, v1.1.0)
  [✓] Product-portfolio association: 1 association (Curated S3 Bucket -> Curated S3 Products)
  [✓] Constraint(s): LAUNCH sc-launch-s3-role (STACK-based, scoped to s3:* + iam:PassRole with tag condition), TAG_UPDATE NOT_ALLOWED, NOTIFICATION sc-launch-events SNS topic
  [✓] TagOptions: 2 key-value pairs bound at portfolio level (CostCenter=platform-1234, Owner=platform-governance)
  [✓] Share(s): ORGANIZATIONAL_UNIT ou-abc1-abcdef (region: us-east-1, delegated admin: enabled)
VERIFICATION_COMMANDS:
  aws servicecatalog describe-portfolio --id port-aaaa1111
  aws servicecatalog search-products-as-admin --portfolio-id port-aaaa1111
  aws servicecatalog describe-constraint --id cons-bbbb2222
  aws servicecatalog list-tag-options
  aws servicecatalog list-portfolio-access --portfolio-id port-aaaa1111
  aws organizations list-delegated-administrators --service-principal servicecatalog.amazonaws.com
```

### Perfect example output — PREREQUISITES_MISSING

```text
PORTFOLIO: Cross-Region VPC Products (products: 0, shares: o-abc123def456 in us-east-1)
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓] Intent + consumer scope: Distribute VPC-creator products to the whole organization, scope ORGANIZATION
  [✗] Portfolio created: pending — deferred until launch role prerequisite is resolved
  [✗] Product(s): pending — CloudFormation template URL not validated
  [—] Product-portfolio association: deferred until product exists
  [✗] Constraint(s): no LAUNCH role exists. Create sc-launch-vpc-role with ec2:* + iam:PassRole (with tag condition) before applying the LAUNCH constraint — without it, products launch as the end-user's role = privilege escalation.
  [—] TagOptions: deferred
  [✗] Share(s): Organizations not enabled for Service Catalog — enable-aws-service-access for servicecatalog.amazonaws.com before sharing at the org level. Region us-east-1 confirmed for caller; document for consumers.
VERIFICATION_COMMANDS:
  aws organizations describe-organization --query 'Organization.Id'
  aws organizations list-delegated-administrators --service-principal servicecatalog.amazonaws.com
  aws iam get-role --role-name sc-launch-vpc-role
  aws cloudformation validate-template --template-url https://s3.amazonaws.com/platform-templates/vpc.yaml
```

**Self-check before emit:**
- [ ] All 7 checklist rows present (no omitted items)?
- [ ] Every `[✓]` has a matching verification command?
- [ ] LAUNCH constraint cites role name + scoping model?
- [ ] Share(s) cite recipient scope AND caller region?
- [ ] TagOptions cite binding level (portfolio vs. product)?
- [ ] Product(s) cite provisioning artifact count + active version?
- [ ] Every `[✗]` cites the specific gap?
- [ ] TEMPLATE-type LAUNCH constraint (if present) carries a `[WARN]`?

## Recent AWS features

- **Service Catalog with Terraform Open Source (2024-2025):** Service
  Catalog now supports Terraform-based products in addition to
  CloudFormation. Products reference a Terraform module from a Git
  repository; Service Catalog manages `terraform apply` and state
  storage. Verify the Terraform engine is registered with Service
  Catalog in your region before publishing Terraform products.
- **Service Catalog with Terraform Cloud (2025):** integrates with
  HCP Terraform / Terraform Cloud for state management, plan
  approval, and policy-as-code (Sentinel). Useful for governance-
  heavy organizations already standardized on Terraform Cloud.
- **Service App Registry integration:** Service Catalog products can
  be associated with Service App Registry applications for unified
  application inventory. The association persists across launches,
  giving operations teams a single view of all deployed applications.
  Verify the application exists before associating.
- **CloudFormation StackSets as a Service Catalog product:** enables
  a product that, when launched, deploys a stack set across multiple
  accounts. Useful for organization-wide rollouts of governance
  primitives (Config rules, CloudTrail, etc.). Requires the launch
  role to have `cloudformation:CreateStackSet`.
- **TagOption inheritance improvements:** TagOptions bound at the
  portfolio level now propagate to all products and to all
  provisioning artifacts of those products. Verify inheritance via
  `list-tag-options` after binding.
- **Delegated administrator for Service Catalog:** allows a member
  account to manage Service Catalog portfolios on behalf of the
  organization. Verify the delegated admin is set before org-level
  shares; otherwise, member accounts can view portfolios but cannot
  manage them.
- **Service Catalog API updates:** new `update-product` and
  `update-portfolio` APIs accept a `SourceProduct` parameter for
  copying products across portfolios. Useful for promoting products
  from a staging portfolio to a production portfolio.

## AWS documentation

- **AWS Service Catalog Administrator Guide** — https://docs.aws.amazon.com/servicecatalog/latest/adminguide/introduction.html
- **Service Catalog Portfolios** — https://docs.aws.amazon.com/servicecatalog/latest/adminguide/catalogs_portfolios.html
- **Service Catalog Products** — https://docs.aws.amazon.com/servicecatalog/latest/adminguide/catalogs_products.html
- **Service Catalog Constraints** — https://docs.aws.amazon.com/servicecatalog/latest/adminguide/constraints.html
- **Service Catalog Launch Constraints** — https://docs.aws.amazon.com/servicecatalog/latest/adminguide/constraints-launch.html
- **Service Catalog TagOptions** — https://docs.aws.amazon.com/servicecatalog/latest/adminguide/tagoptions.html
- **Service Catalog Portfolio Sharing** — https://docs.aws.amazon.com/servicecatalog/latest/adminguide/catalogs_portfolios_sharing.html
- **Service Catalog API Reference** — https://docs.aws.amazon.com/servicecatalog/latest/dg/welcome.html
- **Service Catalog CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/servicecatalog/
- **Blog: Service Catalog + Terraform Open Source** — https://aws.amazon.com/blogs/mt/announcing-aws-service-catalog-support-for-terraform-open-source/
- **Workshop: Service Catalog** — https://catalog.workshops.aws/servicecatalog
