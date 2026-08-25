# Advanced Patterns — Lake Formation Permissions Deployer

Load-on-demand deep dives moved verbatim from SKILL.md.

## Step 8 — IAM Identity Center integration (moved from SKILL.md)

Lake Formation integrates with IAM Identity Center to map Identity
Center groups to Lake Formation principals. This enables SSO-based
access to data lake resources.

```bash
# Enable Lake Formation as a service in Identity Center
aws sso-admin create-application \
  --instance-arn arn:aws:sso:::instance/ssoins-xxxxxxxx \
  --application-provider-configuration '{"ApplicationProviderArn": "arn:aws:sso:::applicationProvider/lakeformation"}' \
  --name "LakeFormation-SSO"

# Grant permissions to an Identity Center group
aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "arn:aws:sso:::permissionSet/ssoins-xxxxxxxx/ps-xxxxxxxx"}' \
  --permissions SELECT DESCRIBE \
  --resource '{"LFTagPolicy": {"ResourceType": "TABLE", "Expression": [{"TagKey": "environment", "TagValues": ["production"]}, {"TagKey": "department", "TagValues": ["finance"]}]}}'
```

Rules:
- **Identity Center groups replace IAM roles as principals.** Use the
  Identity Center permission set ARN or group ARN as the
  `DataLakePrincipalIdentifier`.
- **SSO-enabled access is session-based.** Principals access the data
  lake via Athena/Redshift Spectrum with temporary credentials issued
  by Identity Center.
- **NEVER mix IAM role principals and Identity Center principals for
  the same access pattern.** Choose one model per access pattern to
  avoid permission conflicts.

## Step 9 — LF-tags with Amazon DataZone (moved from SKILL.md)

Amazon DataZone integrates with Lake Formation LF-tags to enable
data marketplace and catalog-driven access. DataZone projects map to
LF-tag expressions for automated access provisioning.

```bash
# Create a DataZone domain (if not exists)
aws datazone create-domain \
  --name "analytics-domain" \
  --domain-execution-role arn:aws:iam::123456789012:role/DataZoneExecutionRole

# Subscribe a DataZone project to LF-tag-based assets
aws datazone create-subscription \
  --domain-identifier dzd-xxxxxxxx \
  --request-name "analytics-team-subscription" \
  --subscribed-listings '[{"ListingId": "lz-xxxxxxxx"}]' \
  --subscription-request-creator "arn:aws:iam::123456789012:role/AnalyticsTeamRole"
```

Rules:
- **DataZone manages the subscription lifecycle.** When a project
  subscribes to a listing backed by LF-tags, DataZone auto-grants
  Lake Formation permissions.
- **LF-tags are the bridge.** DataZone catalog assets map to LF-tag
  expressions. Ensure LF-tags on resources match the DataZone
  classification.

## Recent AWS features detail (moved from SKILL.md)

- **Lake Formation with IAM Identity Center (2024-2026):** SSO-based
  access to data lake resources via Identity Center groups. Replaces
  IAM role principals with Identity Center permission sets and groups
  for session-based access through Athena, Redshift Spectrum, and
  QuickSight.
- **LF-tags with Amazon DataZone (2024-2026):** DataZone catalog
  assets map to LF-tag expressions for automated access provisioning
  via subscriptions. Enables a self-service data marketplace where
  analysts request access and DataZone auto-grants Lake Formation
  permissions.
- **Hybrid access mode (2024-2026):** tables can be accessed via both
  Lake Formation permissions AND IAM/IAM policies simultaneously.
  Enables gradual migration from IAM-based to Lake Formation-based
  access control without breaking existing workloads.
- **Governed Tables (2024-2025):** Lake Formation-managed tables with
  ACID transactions, time travel, and schema evolution. Permissions
  are managed entirely by Lake Formation (no IAM table access).
- **Data cells filter enhancements (2024-2026):** improved filter
  expression evaluation performance and support for nested column
  wildcards. Enables complex row-level security without performance
  degradation.
- **Resource link cross-account via RAM (2024-2025):** RAM resource
  shares for cross-account resource links, enabling multi-account
  data lake architectures without duplicated grants.
- **LF-tag auditing via CloudTrail (2024-2026):** all LF-tag CRUD
  operations and permission grants are logged to CloudTrail for
  compliance auditing.
- **Column-level security with wildcard exclusion (2024-2025):**
  `ColumnWildcard.ExcludedColumnNames` grants access to all columns
  except the excluded ones. Simplifies PII protection — grant all,
  exclude sensitive.

## Expert heuristic — LF-tag strategy, column security, and migration

- **LF-tag design:** use 3-5 tag keys that map to organizational
  dimensions. Recommended: `environment` (production/staging/dev),
  `department` (finance/engineering/marketing), `sensitivity`
  (public/internal/restricted/pii). More than 7 keys makes the model
  unmaintainable.
- **LF-tag vs named resource grants:** use LF-tag-based grants for
  dynamic access (new tables auto-inherit access via tags). Use named
  resource grants for static access (specific table for a specific
  role). LF-tag is preferred for production; named resource for
  dev/test.
- **Column-level security strategy:** use column grant for simple
  cases (grant subset of columns). Use data cells filter for complex
  cases (row-level + column-level filtering with conditions). Data
  cells filter is more expressive but adds query overhead.
- **PII protection:** use `ColumnWildcard.ExcludedColumnNames` in data
  cells filter to grant all columns except PII. This is more
  maintainable than enumerating every non-PII column — new columns
  are automatically accessible.
- **Resource links for cross-database:** create a resource link in the
  target database pointing to the source table. Grant DESCRIBE on the
  link AND SELECT on the target table. Without both, queries fail
  with "table not found" or "access denied."
- **Hybrid access mode migration:** enable hybrid access on tables
  that have existing IAM policy access. Lake Formation permissions
  overlay IAM policies. Once all access is via Lake Formation,
  disable IAM table access and switch to Lake Formation-only mode.
- **IAM Identity Center for SSO:** prefer Identity Center over IAM
  roles for human-principal access. Identity Center provides
  session-based, auditable access via SSO. IAM roles are for
  service-to-service access.
- **DataZone for self-service:** use DataZone for analyst-facing data
  marketplace. DataZone subscriptions auto-grant Lake Formation
  permissions via LF-tag expressions. Reduces the admin burden of
  manual grants.
