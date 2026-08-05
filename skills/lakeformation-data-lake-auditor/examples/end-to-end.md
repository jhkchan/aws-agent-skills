# End-to-end usage scenario: lakeformation-data-lake-auditor

A walkthrough showing the skill auditing a Lake Formation data lake that
combines three findings — a ColumnWildcard SELECT on a PII-tagged table
(OVERPERMISSIVE_GRANT), a missing DataCellsFilter on the same table
(CONFIG_GAP additive), and an empty DataLakeAdmins list (CONFIG_GAP). It
demonstrates severity aggregation, the no-Deny / WithGrantablePermissions
delegation concepts, and the revoke-after-replace remediation workflow.

## Input (user prompt)

> Audit this Lake Formation data lake before the production cutover. We
> migrated from IAM-based access last quarter and I want to make sure LF
> is actually enforcing what we think it is.

```text
Audit target (catalog): 111111111111 (multi-finding-walkthrough)
Lake Formation enabled: true (describe-organization)
Data lake settings (get-data-lake-settings):
  DataLakeAdmins: []
Registered locations (list-resources):
  - ResourceArn: arn:aws:s3:::prod-datalake/customer/
    RoleArn: arn:aws:iam::111111111111:role/aws-service-role/lakeformation/ApplicationRole
Data cells filters (list-data-cells-filter): []
LF-tags on table customers_pii:
  - data_classification=PII
Table storage descriptor:
  - customers_pii location: s3://prod-datalake/customer/customers_pii/
Permissions (list-permissions):
  [
    {
      "Principal": {"DataLakePrincipalIdentifier": "arn:aws:iam::111111111111:role/analyst"},
      "Resource": {"TableWithColumns": {"DatabaseName": "customers", "Name": "customers_pii", "CatalogId": "111111111111", "ColumnWildcard": {}}},
      "Permissions": ["SELECT"],
      "PermissionsWithGrantOptions": ["SELECT"]
    }
  ]
```

## Expected output (VERDICT block)

```text
LAKE: 111111111111 (multi-finding-walkthrough)
VERDICT: OVERPERMISSIVE_GRANT
REASON: analyst role holds SELECT with ColumnWildcard on the PII-tagged
customers_pii table (Step 3) — full-column read including ssn/email/phone.
WithGrantablePermissions chains unbounded (Step 4). No DataCellsFilter is
wired (Step 7) and DataLakeAdmins is empty (Step 6).
FINDINGS:
  - [OVERPERMISSIVE_GRANT] SELECT with ColumnWildcard on table.customers_pii
    to arn:aws:iam::111111111111:role/analyst (Step 3) — all columns on a
    PII-tagged table.
  - [OVERPERMISSIVE_GRANT] WithGrantablePermissions includes SELECT — the
    analyst can re-delegate SELECT on this table to any other principal,
    indefinitely (Step 4).
  - [CONFIG_GAP] No DataCellsFilter references table.customers_pii (Step 7)
    — column-scoping is absent AND row-level exposure is unbounded.
  - [CONFIG_GAP] DataLakeAdmins is empty (Step 6) — no break-glass admin
    can manage LF resources without an explicit grant.
REMEDIATION:
  1. Snapshot current grants:
     aws lakeformation list-permissions --output json > /tmp/lf-backup-$(date +%s).json
  2. Add the narrow replacement BEFORE revoking the wildcard:
     aws lakeformation grant-permissions \
       --principal arn:aws:iam::111111111111:role/analyst \
       --permissions SELECT \
       --resource '{"TableWithColumns":{"DatabaseName":"customers","Name":"customers_pii","CatalogId":"111111111111","ColumnNames":["customer_id","region","lifetime_value"]}}'
  3. Create and grant a region-scoping DataCellsFilter:
     aws lakeformation create-data-cells-filter --table-data '<...>'
  4. Revoke the wildcard grant (now redundant after steps 2-3):
     aws lakeformation revoke-permissions \
       --principal arn:aws:iam::111111111111:role/analyst \
       --permissions SELECT \
       --resource '{"TableWithColumns":{"DatabaseName":"customers","Name":"customers_pii","CatalogId":"111111111111","ColumnWildcard":{}}}'
  5. Designate 1-3 break-glass admin roles and apply:
     aws lakeformation put-data-lake-settings \
       --data-lake-settings '{"DataLakeAdmins":[{"DataLakePrincipalIdentifier":"arn:aws:iam::111111111111:role/lf-break-glass"}]}'
```

## Key reasoning the skill contributes

- **No-Deny awareness.** The operator cannot "add a Deny" to block the
  ColumnWildcard — the only remediation is to revoke after the narrow
  replacement is in place. Reversing the order creates an access-denied
  window for the analyst.
- **WithGrantablePermissions chain depth is unbounded.** Unlike KMS grants
  (capped at 2 levels), the analyst may have already re-delegated SELECT to
  other principals during the exposure window. Audit CloudTrail for
  `lakeformation:GrantPermissions` calls by the analyst and revoke any
  downstream grants.
- **DataCellsFilter wiring gap.** Even after the column-scope fix, every
  row in the table remains readable by the analyst. A column-scoped SELECT
  without a DataCellsFilter is column-least-privilege but NOT row-least-
  privilege.
- **Empty DataLakeAdmins.** With no admins, no one can break-glass into
  the data lake if the analyst role is deleted or its trust policy breaks.
  This is an operational risk independent of the grant-level findings.
