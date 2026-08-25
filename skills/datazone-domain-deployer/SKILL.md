---
name: datazone-domain-deployer
description: 'Provisions Amazon DataZone data domains with production defaults: domain creation (create-datazone-domain), project management, data source connections (S3, Redshift, RDS), asset management (data inventory, glossary terms), metadata enrichment via Lambda-based auto-classification, subscription workflows (request-approve model), cross-account IAM role chaining for data access, blueprints (data lake, data warehouse), environment profiles, SSO federation for user management, and metadata forms. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a DataZone domain, setting up projects, configuring data source connections, establishing subscription workflows, configuring cross-account IAM roles, or deploying blueprints. Triggers: create datazone domain, datazone project, data source connection, subscription workflow, cross-account data access, datazone blueprint, environment profile, glossary governance, metadata enrichment, SSO federation datazone.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with datazone and ram access. Works with Terraform aws_datazone_domain / aws_datazone_project / aws_datazone_environment_blueprint resources and CloudFormation AWS::DataZone::Domain / AWS::DataZone::Project templates. Cross-account data access requires RAM resource share and IAM role trust policies.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, datazone, cloudops, deploy, analytics, provisioning, domain, project, subscription, glossary, blueprint, cross-account, iam-role-chaining, metadata
  dependencies: aws-orchestrator
  keywords: aws, datazone, data catalog, cloudops, deploy, provisioning, domain, project, data source, subscription, glossary, metadata, blueprint, environment profile, cross-account, iam role chaining, sso federation, asset management
  when_to_use: Invoke when the user wants to create an Amazon DataZone domain, manage projects, configure data source connections (S3, Redshift, RDS), set up subscription workflows (request-approve model), configure cross-account IAM role chaining for data access, deploy blueprints (data lake, data warehouse), configure environment profiles, establish glossary-driven governance, or enable metadata enrichment. Do NOT invoke for AWS Lake Formation (use Lake Formation skills), AWS Glue Data Catalog (use Glue skills), or Amazon Athena (use Athena skills).
---

# Amazon DataZone Domain Deployer

An AWS CloudOps agent skill that provisions Amazon DataZone data
domains with correct defaults. The skill walks the operator through
domain creation, project management, data source connections (S3,
Redshift, RDS), asset management with glossary terms, metadata
enrichment via Lambda-based auto-classification, subscription
workflows (request-approve model), cross-account IAM role chaining
for data access, blueprints (data lake, data warehouse), environment
profiles, SSO federation for user management, and metadata forms,
captures all governance and access decisions, explains why each
default matters, and emits a READY_TO_DEPLOY checklist with copy-
pasteable verification commands.

## Activation keywords

create DataZone domain, DataZone project, data source connection,
subscription workflow, cross-account data access, DataZone blueprint,
environment profile, glossary governance, metadata enrichment, SSO
federation DataZone.

## STRICT output contract

When this skill is invoked with a DataZone-provisioning request
(create a domain, create a project, configure a data source, set up
subscriptions, configure cross-account IAM roles, deploy blueprints,
or a partial configuration), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in the "Output format" section using
the literal all-caps labels `DATAZONE:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Domain creation | Core domain model |
| Step 2 — Project management | Project scoping |
| Step 3 — Data source connections (S3, Redshift, RDS) | Data ingestion |
| Step 4 — Asset management and glossary terms | Data inventory |
| Step 5 — Metadata enrichment (Lambda auto-classification) | Auto-tagging |
| Step 6 — Subscription workflows (request-approve) | Access governance |
| Step 7 — Cross-account IAM role chaining | Cross-account data access |
| Step 8 — Blueprints (data lake, data warehouse) | Environment templates |
| Step 9 — Environment profiles | Deployment targets |
| Step 10 — SSO federation and user management | Identity |
| Step 11 — Metadata forms | Custom metadata |
| Step 12 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/cross-account-and-subscriptions.md | IAM chaining + subscription detail |
| references/blueprints-and-governance.md | Blueprints + glossary detail |

## Mindset

Mindset framing and the three misconceptions (domain alone does not share data, subscriptions are request-approve by design, glossary terms are the policy engine not labels) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand before designing any DataZone deployment.

## Configuration dependency graph (novel heuristic)

Configuration dependency graph (domain → project → data source → asset → glossary → subscription → cross-account role → blueprint → profile → enrichment) with hard-dependency, silent-failure, and downstream columns moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand to sequence provisioning in the correct order.

## Expert heuristic: cross-account IAM role chaining

Cross-account heuristic (three-hop role chain: DataZone service → hub execution role → source-account role, with the critical trust-policy JSON) moved verbatim to [references/cross-account-and-subscriptions.md](references/cross-account-and-subscriptions.md).
Load on demand when connecting cross-account data sources.

## Expert heuristic: subscription approval workflow

Subscription heuristic (lifecycle PENDING → APPROVED/REJECTED and glossary-term-driven approval routing: Public auto-approve, Internal owner, PII steward, Restricted executive) moved verbatim to [references/cross-account-and-subscriptions.md](references/cross-account-and-subscriptions.md).
Load on demand when designing the approval workflow.

## Expert heuristic: glossary-driven governance

Glossary heuristic (hierarchy example: Data Classification / Data Domain / Data Quality categories and their subscription policies) moved verbatim to [references/blueprints-and-governance.md](references/blueprints-and-governance.md).
Load on demand when designing glossary governance.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS region supports DataZone | DataZone is available in select regions | `aws datazone list-domains --region <region>` |
| IAM Identity Center (SSO) configured | DataZone requires SSO for user management — no IAM users | `aws sso-admin list-instances` |
| Domain name (3-63 chars, alphanumeric + hyphen) | Domain name must be unique | Naming convention check |
| Source account ID (if cross-account data) | Cross-account requires both account IDs | `aws sts get-caller-identity` in source account |
| IAM role in source account (if cross-account) | DataZone domain must assume a role in the source account to read data | `aws iam get-role --role-name DataZoneS3AccessRole` in source account |
| S3 bucket exists (if S3 data source) | Data source must reference an existing bucket | `aws s3api head-bucket --bucket <name>` |
| Redshift cluster/serverless namespace (if Redshift source) | Data source must reference an existing cluster | `aws redshift describe-clusters` or `aws redshift-serverless list-namespaces` |
| Secrets Manager secret for Redshift credentials | Redshift connection requires a secret with db credentials | `aws secretsmanager describe-secret --secret-id <id>` |
| KMS key for domain encryption (if CMK) | Domain data is encrypted; CMK provides auditability | `aws kms describe-key --key-id <key-id>` |
| IAM permissions for datazone:* | Provisioning requires domain/project create permissions | Verify IAM policy |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Domain creation

A DataZone domain is the top-level container for all data management
resources (projects, data sources, assets, glossaries).

Step 1 create-domain CLI (name, description, domain-execution-role, KMS key) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when creating the domain.

**Critical:** the `--domain-execution-role` must exist before creating
the domain. This role is assumed by the DataZone service to perform
cross-account operations (reading data sources, provisioning
environments). The role's trust policy must allow
`datazone.amazonaws.com` to assume it.

Step 1 get-domain status poll (expected AVAILABLE) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when waiting for asynchronous domain creation.

## Step 2 — Project management

Projects organize users, data sources, and environments within a
domain. Each project has a project owner and members.

```bash
# Create a project in the domain
PROJECT_ID=$(aws datazone create-project \
  --domain-id "$DOMAIN_ID" \
  --name customer-analytics \
  --description "Customer analytics project with S3 and Redshift sources" \
  --region us-east-1 \
  --query 'id' --output text)

echo "Project ID: $PROJECT_ID"
```

**Project roles:**
- **Project owner:** can manage project settings, approve/reject
  subscriptions, add/remove members.
- **Project member:** can discover assets, request subscriptions,
  and consume published data.
- **Project viewer:** can browse the catalog but cannot request
  subscriptions.

## Step 3 — Data source connections (S3, Redshift, RDS)

Data source connections link external data stores to a DataZone
project. DataZone auto-discovers assets (tables, files, views) from
the connected source.

Step 3 connection CLI for all three source types (create-data-source + create-connection with S3 location, Redshift clusterId + secretArn, RDS instanceId + secretArn) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when wiring data source connections.

**Critical:** the `roleArn` in each connection references an IAM role
in the SOURCE account (222222222222). That role must have a trust
policy allowing the DataZone domain account's execution role to
assume it. Without this, DataZone cannot read any data from the
source.

## Step 4 — Asset management and glossary terms

Assets are auto-discovered from data sources. Each asset (S3 object,
Redshift table, RDS table) becomes a catalogable item. Assets must be
PUBLISHED before they appear in the catalog and can be subscribed to.

Step 4 CLI (list-assets, update-asset --status PUBLISHED) moved verbatim to [references/blueprints-and-governance.md](references/blueprints-and-governance.md).
Load on demand when publishing discovered assets.

### Glossary terms

Glossary terms classify assets and drive subscription policies.

Step 4 CLI (create-glossary-term, associate-glossary-term-with-asset) moved verbatim to [references/blueprints-and-governance.md](references/blueprints-and-governance.md).
Load on demand when tagging assets with glossary terms.

## Step 5 — Metadata enrichment (Lambda auto-classification)

Step 5 enrichment walkthrough (create-function, register with a DataZone environment, and the PII-detecting Lambda handler) moved verbatim to [references/blueprints-and-governance.md](references/blueprints-and-governance.md).
Load on demand when automating glossary tagging.

## Step 6 — Subscription workflows (request-approve model)

Subscriptions govern data access. A consumer requests access to a
published asset; the asset owner approves or rejects.

Step 6 CLI (create-subscription request, get-subscription PENDING check, update-subscription APPROVED) moved verbatim to [references/cross-account-and-subscriptions.md](references/cross-account-and-subscriptions.md).
Load on demand when driving the request-approve flow.

**Subscription statuses:** PENDING → APPROVED (access granted) |
REJECTED (access denied) | REVOKED (access withdrawn after approval).

**Glossary-term-driven routing:** assets tagged with glossary terms
that have subscription policies route approval requests to the
designated approver. For example, assets tagged "PII" route to the
data steward; assets tagged "Public" may auto-approve.

## Step 7 — Cross-account IAM role chaining

Cross-account data access requires a role chain: the DataZone domain
account's execution role assumes a role in the data source account.

Step 7 CLI (iam create-role with the execution-role trust principal, put-role-policy S3 read) moved verbatim to [references/cross-account-and-subscriptions.md](references/cross-account-and-subscriptions.md).
Load on demand when provisioning the source-account role.

**Critical:** the trust policy `Principal` must be the FULL ARN of
the DataZone domain's execution role, not just the account ID. Using
the account ID (`arn:aws:iam::111111111111:root`) is less secure
because it allows any role in the domain account to assume the source
role.

## Step 8 — Blueprints (data lake, data warehouse)

Blueprints are AWS-managed templates that define environment
defaults. DataZone provides two primary blueprints.

| Blueprint | Description | Default resources |
|---|---|---|
| **Default Data Lake** | S3-based data lake environment | S3 bucket, Glue database, Lake Formation permissions |
| **Default Data Warehouse** | Redshift-based data warehouse environment | Redshift cluster, database, IAM roles |

Step 8 CLI (list-environment-blueprints, update-environment-blueprint --enabled) moved verbatim to [references/blueprints-and-governance.md](references/blueprints-and-governance.md).
Load on demand when enabling a blueprint.

**Blueprints define WHAT is provisioned** (data lake vs data
warehouse defaults). **Environment profiles determine WHERE it is
provisioned** (which account and region).

## Step 9 — Environment profiles

Environment profiles map blueprint defaults to specific deployment
targets (AWS account and region).

Step 9 CLI (create-environment-profile mapped to account/region with s3BucketName/glueDatabaseName parameters) moved verbatim to [references/blueprints-and-governance.md](references/blueprints-and-governance.md).
Load on demand when creating deployment targets.

**Environment profiles are project-scoped:** each project can have
its own profiles pointing to different accounts or regions.

## Step 10 — SSO federation and user management

DataZone uses IAM Identity Center (SSO) for user management. All
users must be provisioned through SSO — DataZone does NOT support IAM
users.

Step 10 CLI (sso-admin list-instances, identitystore list-users) moved verbatim to [references/cross-account-and-subscriptions.md](references/cross-account-and-subscriptions.md).
Load on demand when verifying IAM Identity Center wiring.

**User roles in DataZone:**
- **Domain admin:** can manage domain settings, all projects, and
  all blueprints.
- **Project owner:** can manage project settings, approve/reject
  subscriptions for assets in the project.
- **Project member:** can discover assets, request subscriptions,
  and consume published data.
- **Project viewer:** can browse the catalog but cannot request
  subscriptions.

**SSO groups** can be used to assign roles at scale. Instead of
adding individual users, add an SSO group as a project member.

## Step 11 — Metadata forms

Metadata forms are custom metadata templates that can be attached to
assets. They provide structured metadata beyond what the glossary
offers.

Step 11 CLI (create-form-type DataQualityMetrics model, post-form-data on an asset) moved verbatim to [references/blueprints-and-governance.md](references/blueprints-and-governance.md).
Load on demand when attaching structured metadata.

## Step 12 — Recent features

Recent AWS features (SageMaker auto-classification, cross-account subscription workflows, API GA, glossary policy engine, custom blueprints, metadata form enhancements, business catalog) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand before recommending 2023-2026 capabilities.

## NEVER do these things

1. **NEVER skip the cross-account IAM role setup.** DataZone operates
   in a hub-and-spoke model. The domain account's execution role must
   be able to assume a role in each source account. Without this
   trust chain, data sources connect but all reads fail silently with
   Access Denied.

2. **NEVER assume subscriptions are auto-approved.** DataZone uses a
   request-approve model by design. Subscriptions require explicit
   approval from the asset owner or delegated approver. Auto-approval
   can be configured but defeats the governance purpose.

3. **NEVER treat glossary terms as just labels.** Glossary terms are
   the policy engine. They carry subscription policies that determine
   approval routing. An asset tagged "PII" requires data steward
   approval; an asset tagged "Public" may auto-approve. Design the
   glossary BEFORE publishing assets.

4. **NEVER use the account ID in the cross-account trust policy
   instead of the full role ARN.** Using
   `arn:aws:iam::111111111111:root` in the Principal is less secure
   than using the full execution role ARN
   (`arn:aws:iam::111111111111:role/service-role/AmazonDataZoneDomainExecution`).
   The full ARN restricts assumption to the specific role.

5. **NEVER assume glossary policies are retroactive.** If you add a
   subscription policy to a glossary term after assets are published
   and subscriptions are approved, existing subscriptions are NOT re-
   evaluated. The glossary must be designed before publishing assets.

6. **NEVER try to use IAM users with DataZone.** DataZone requires
   IAM Identity Center (SSO) for all user management. IAM users are
   not supported. All users must be provisioned through the SSO
   directory.

7. **NEVER publish assets without glossary terms.** Assets without
   glossary terms have no governance policy. Every published asset
   should be classified with at least a data classification term
   (Public, Internal, Confidential, Restricted).

8. **NEVER forget to verify domain status is AVAILABLE before
   creating projects.** Domain creation is asynchronous. Creating a
   project before the domain is AVAILABLE will fail. Always poll the
   domain status.

9. **NEVER confuse blueprints with environment profiles.** Blueprints
   define WHAT is provisioned (data lake vs data warehouse defaults).
   Environment profiles define WHERE it is provisioned (which account
   and region). Both are needed.

10. **NEVER skip metadata enrichment for large catalogs.** Manual
    tagging of thousands of assets is unsustainable. Always configure
    Lambda-based or SageMaker-based auto-classification for metadata
    enrichment to keep glossary tags current.

## Output format

```text
DATAZONE: <domain-name> (<domain-id>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Domain: <domain-name> (<domain-id>) — AVAILABLE
  [✓|✗] Domain execution role: <role-arn>
  [✓|✗] SSO/IAM Identity Center: configured (identity store: <store-id>)
  [✓|✗] Project: <project-name> (<project-id>) — project owner: <owner>
  [✓|✗] Data source: <source-name> (S3 | Redshift | RDS) — connection established
  [✓|✗] Cross-account IAM role: <source-role-arn> — trust policy verified
  [✓|✗] Assets: discovered and published (<N> assets in catalog)
  [✓|✗] Glossary: <N> terms configured — subscription policies attached
  [✓|✗] Metadata enrichment: Lambda auto-classification configured
  [✓|✗] Subscription workflow: request-approve model — approver: <approver>
  [✓|✗] Blueprint: Default Data Lake | Default Data Warehouse — enabled
  [✓|✗] Environment profile: <profile-name> → account <acct>, region <region>
  [✓|✗] Encryption: KMS CMK (<kms-key-alias>) | AWS-managed key
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws datazone get-domain --domain-id <domain-id>
  aws datazone list-projects --domain-id <domain-id>
  aws datazone list-data-sources --domain-id <domain-id>
  aws datazone list-assets --domain-id <domain-id>
  aws datazone list-glossary-terms --domain-id <domain-id>
```

### Worked example — domain with S3 source and subscription governance

```text
DATAZONE: analytics-domain (domain-aaa11122)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Domain: analytics-domain (domain-aaa11122) — AVAILABLE
  [✓] Domain execution role: arn:aws:iam::111111111111:role/service-role/AmazonDataZoneDomainExecution
  [✓] SSO/IAM Identity Center: configured (identity store: d-abc12345)
  [✓] Project: customer-analytics (project-bbb22233) — project owner: data-steward@corp
  [✓] Data source: customer-events-s3 (S3) — connection established
  [✓] Cross-account IAM role: arn:aws:iam::222222222222:role/DataZoneS3AccessRole — trust policy verified
  [✓] Assets: discovered and published (42 assets in catalog)
  [✓] Glossary: 15 terms configured — subscription policies attached (PII → steward approval, Public → auto-approve)
  [✓] Metadata enrichment: Lambda auto-classification configured (datazone-auto-classify)
  [✓] Subscription workflow: request-approve model — approver: data-steward@corp
  [✓] Blueprint: Default Data Lake — enabled
  [✓] Environment profile: production-data-lake → account 222222222222, region us-east-1
  [✓] Encryption: KMS CMK (alias/datazone-cmk)
  [✓] Tags: Environment=production, Domain=analytics
VERIFICATION_COMMANDS:
  aws datazone get-domain --domain-id domain-aaa11122
  aws datazone list-projects --domain-id domain-aaa11122
  aws datazone list-data-sources --domain-id domain-aaa11122
  aws datazone list-assets --domain-id domain-aaa11122
  aws datazone list-glossary-terms --domain-id domain-aaa11122
```

## Error handling

Error-handling deep dives (zero-asset crawl, InvalidDomainExecutionRole, PENDING subscriptions, SSO users invisible, publish failures, cross-account provisioning failures) moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when a deployment step fails.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Mindset misconceptions, configuration dependency graph, and Recent AWS features moved from SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — domain-creation and data-source-connection CLI moved from SKILL.md
- [references/error-handling.md](references/error-handling.md) — failure-mode deep dives moved from SKILL.md
- [references/cross-account-and-subscriptions.md](references/cross-account-and-subscriptions.md) — cross-account/subscription heuristics and Step 6/7/10 CLI moved from SKILL.md (pre-existing; extended)
- [references/blueprints-and-governance.md](references/blueprints-and-governance.md) — glossary heuristic and Step 4/5/8/9/11 CLI moved from SKILL.md (pre-existing; extended)

## Domain

AWS CloudOps / Amazon DataZone Data Domain Provisioning, Data
Cataloging, Governance, and Cross-Account Data Sharing.

## AWS documentation

- **Amazon DataZone User Guide** — https://docs.aws.amazon.com/datazone/latest/userguide/what-is-datazone.html
- **Create domain** — https://docs.aws.amazon.com/datazone/latest/userguide/create-domain.html
- **Create project** — https://docs.aws.amazon.com/datazone/latest/userguide/create-project.html
- **Data source connections** — https://docs.aws.amazon.com/datazone/latest/userguide/data-sources.html
- **Subscription workflows** — https://docs.aws.amazon.com/datazone/latest/userguide/subscriptions.html
- **Cross-account access** — https://docs.aws.amazon.com/datazone/latest/userguide/cross-account-access.html
- **Glossary and governance** — https://docs.aws.amazon.com/datazone/latest/userguide/glossary.html
- **Blueprints** — https://docs.aws.amazon.com/datazone/latest/userguide/blueprints.html
- **Environment profiles** — https://docs.aws.amazon.com/datazone/latest/userguide/environment-profiles.html
- **Metadata enrichment** — https://docs.aws.amazon.com/datazone/latest/userguide/metadata-enrichment.html
- **IAM Identity Center integration** — https://docs.aws.amazon.com/datazone/latest/userguide/sso-integration.html
- **DataZone API** — https://docs.aws.amazon.com/datazone/latest/APIReference/Welcome.html
