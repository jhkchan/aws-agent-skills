---
description: Provision an Amazon DataZone data domain with production-grade defaults (domain creation, project management, data source connections for S3/Redshift/RDS, cross-account IAM role chaining, glossary-driven governance with subscription policies, metadata enrichment via Lambda auto-classification, subscription request-approve workflows, blueprints, environment profiles, SSO federation). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create datazone domain"
  - "datazone project"
  - "data source connection"
  - "subscription workflow"
  - "cross-account data access"
  - "datazone blueprint"
  - "environment profile"
  - "glossary governance"
  - "metadata enrichment"
  - "sso federation datazone"
  - "deploy datazone"
  - "datazone domain"
  - "data catalog domain"
  - "datazone glossary"
  - "datazone subscription"
routes_to: datazone-domain-deployer
---

# /aws:deploy-datazone-domain

Activate the `datazone-domain-deployer` skill and provision an Amazon
DataZone data domain with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Domain creation (top-level container)
2. Project management (users and data source scoping)
3. Data source connections (S3, Redshift, RDS)
4. Asset management and glossary terms (data inventory + classification)
5. Metadata enrichment (Lambda auto-classification)
6. Subscription workflows (request-approve model)
7. Cross-account IAM role chaining (data access across accounts)
8. Blueprints (data lake, data warehouse templates)
9. Environment profiles (deployment target mapping)
10. SSO federation (IAM Identity Center user management)
11. Metadata forms (custom structured metadata)
12. Recent features (SageMaker auto-classification, custom blueprints)

## When to use

- You need to create a DataZone domain.
- You are connecting S3, Redshift, or RDS data sources.
- You need cross-account data access via IAM role chaining.
- You are setting up subscription workflows (request-approve model).
- You need glossary-driven governance with subscription policies.
- You need environment blueprints and profiles.
- You need Lambda-based metadata enrichment (auto-classification).

## When NOT to use

- **AWS Lake Formation** — different service, use Lake Formation skills.
- **AWS Glue Data Catalog** — use Glue skills.
- **Amazon Athena** — use Athena skills.
- **Auditing existing DataZone domains** — use audit skills.

## How to invoke

### Slash command

```
/aws:deploy-datazone-domain
```

Then provide: domain name, project name, data source type and
connection details, source account ID, IAM role names, glossary terms
and policies, blueprint selection, environment profile target, KMS key
(if CMK), tags.

### Natural language

Any of these routes to the same skill:

- "create a DataZone domain called analytics-domain"
- "set up a DataZone project with an S3 data source"
- "configure cross-account IAM role for DataZone"
- "create glossary terms with subscription policies"
- "enable the Default Data Lake blueprint"
- "set up Lambda metadata enrichment for DataZone"

### CLI routing

```bash
node cli/bin/cli.js route "create a datazone domain"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create DataZone
domains or configure data governance. The output checklist feeds into
verification pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-datazone-domain

     Create an Amazon DataZone domain called analytics-domain
     in account 111111111111. Project customer-analytics.
     S3 data source my-customer-events in account
     222222222222 with IAM role DataZoneS3AccessRole.
     Glossary terms PII (steward approval) and Public
     (auto-approve). Tags: Environment=production.

Skill:
  DATAZONE: analytics-domain (domain-aaa11122)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Domain: analytics-domain — AVAILABLE
    [✓] Cross-account IAM role: DataZoneS3AccessRole — trust verified
    [✓] Glossary: PII (steward approval), Public (auto-approve)
    [✓] Subscription workflow: request-approve model
  VERIFICATION_COMMANDS:
    aws datazone get-domain --domain-id domain-aaa11122
    aws datazone list-data-sources --domain-id domain-aaa11122
```

## References

- Skill definition: `skills/datazone-domain-deployer/SKILL.md`
- Cross-account and subscription guide: `skills/datazone-domain-deployer/references/cross-account-and-subscriptions.md`
- Blueprints and governance guide: `skills/datazone-domain-deployer/references/blueprints-and-governance.md`
- Eval suite: `skills/datazone-domain-deployer/evals/evals.json`
