---
description: Provision production-grade AWS Lake Formation permissions including LF-tag based access control, column-level security, data cells filter, resource links, and IAM Identity Center / DataZone integration.
nl_triggers:
  - "grant lake formation permissions"
  - "deploy lake formation permissions"
  - "lf-tag based access control"
  - "lake formation column-level security"
  - "lake formation data cells filter"
  - "lake formation resource links"
  - "register data lake admin"
  - "lake formation iam identity center"
  - "lake formation datazone"
  - "lake formation database permissions"
  - "lake formation table permissions"
  - "configure lf-tags"
  - "lake formation hybrid access mode"
routes_to: lakeformation-permissions-deployer
---

# /aws:deploy-lakeformation-permissions

Activate the `lakeformation-permissions-deployer` skill and produce a
deployment plan for production-grade AWS Lake Formation permissions.

## What it does

Reads a deployment specification (data lake admin, LF-tag keys and
values, LF-tag attachment to databases/tables/columns, principals,
permission grants, column-level security, data cells filter, resource
links, IAM Identity Center integration, DataZone subscription) and
produces an ordered deployment plan with:

1. Admin-first ordering — a data lake admin MUST be registered before
   any LF-tag or permission operation. Without an admin, all Lake
   Formation API calls fail.
2. LF-tag keys and values — define tag keys (environment, department,
   sensitivity) BEFORE attaching to resources. Tag keys are immutable.
3. LF-tag attachment — attach LF-tags to Glue databases, tables, and
   columns BEFORE granting tag-based permissions. Without tags on
   resources, grants match nothing (silent zero access).
4. Principal grants — grant DESCRIBE, SELECT, INSERT, ALTER, DROP on
   LF-tag expressions to IAM principals (roles, users, Identity Center
   groups).
5. Column-level security — column grant (subset of columns) and column
   deny (explicit revoke on PII columns).
6. Data cells filter — row-level + column-level filtering with filter
   expressions (e.g., region = 'us-east-1').
7. Resource links (optional) — cross-database table references with
   dual grants (DESCRIBE on link, SELECT on target table).
8. IAM Identity Center (optional) — SSO-based access via Identity
   Center groups and permission sets.
9. Amazon DataZone (optional) — self-service data marketplace with
   LF-tag-backed subscriptions.
10. Verification — post-deployment list-permissions, get-resource-lf-tags,
    and describe-resource commands.

Emits a deterministic deployment plan:

```text
PERMISSION_DEPLOYMENT: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [x] Data lake admin registered
  [x] LF-tag keys created
  [x] LF-tags attached to databases and tables
  [x] Principal granted LF-tag-based permissions
  [x] Column-level security configured (PII excluded)
  ...
VERIFICATION_COMMANDS:
  <ordered list of aws lakeformation commands>
```

## When to invoke

Provide a deployment spec and ask any of:

- "grant Lake Formation permissions to a principal"
- "set up LF-tag based access control"
- "configure column-level security for PII columns"
- "create a data cells filter for row-level access"
- "register a data lake admin"
- "create a cross-database resource link"
- "integrate Lake Formation with IAM Identity Center"

A bare principal + table + "grant Lake Formation" also routes here
via the orchestrator.

## Inputs

- **Required:** data_lake_admin_arn, target_database, target_table
  (or LF-tag expression), principal_arn.
- **Recommended:** lf_tag_keys (with values), lf_tag_attachments,
  permissions (DESCRIBE, SELECT, INSERT), column_level_grants.
- **Optional:** data_cells_filter (row filter, column wildcard
  exclusion), resource_links (cross-database), iam_identity_center
  groups, datazone_subscription, hybrid_access_mode, tags.

## Outputs

- One VERDICT block per deployment (READY_TO_DEPLOY or
  PREREQUISITES_MISSING).
- CHECKLIST with all deployment dimensions validated.
- VERIFICATION_COMMANDS with ordered
  `aws lakeformation`, `aws glue`, `aws iam`, and `aws sso-admin`
  commands.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill
  is the Phase 1 Deploy specialist for Lake Formation permissions).
- `/aws:audit-lakeformation-data-lake` for post-deployment auditing
  of Lake Formation data lake configuration and permission hygiene.
- `/aws:audit-glue-crawler-job` for Glue Data Catalog and crawler
  auditing (related but separate service).
