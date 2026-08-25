# Diagnostic Commands — cloudtrail-lake-operator

## Live-account pre-flight (EDS + Athena federation gate)

**Live-account pre-flight (skip if offline plan audit):**
1. `aws cloudtrail list-event-data-stores` — find the target EDS by
   `Name`, capture `EventDataStoreArn`, `Status`, `KmsKeyId`,
   `IsOrganizationsEnabled`, `EventConfigurations`.
2. `aws cloudtrail get-event-data-store --event-data-store <id>` —
   capture `Status` (`ENABLED`, `DELETING`, `PENDING_DELETION`),
   `AdvancedEventSelectors`, `RetentionPeriod`, `TerminationProtectionEnabled`.
3. For SSE-KMS EDS: `aws kms describe-key --key-id <kms-key-id>` and
   `get-key-policy --key-id <kms-key-id> --policy-name default` —
   confirm `cloudtrail.amazonaws.com` has `kms:GenerateDataKey`,
   `kms:Decrypt`.
4. `aws organizations describe-organization` — if the EDS is
   org-scoped, confirm the caller is the management account.
5. `aws cloudtrail describe-query --event-data-store <id> --query-id
   <id>` — for the most recent query, capture `QueryStatus`,
   `QueryRunTimeInSeconds`, `BytesScanned`, `ResultsCount`.
6. `aws cloudtrail get-query` (deprecated alias: `get-query`) — for
   diagnosing a failed query, capture `ErrorMessage`.
7. For Athena federation: `aws athena list-work-groups` — confirm
   the workgroup exists; `aws lakeformation list-permissions` —
   confirm the CloudTrailLake connector Lambda has permissions on
   the underlying EDS.
8. For QuickSight: `aws quicksight describe-account-settings` —
   confirm QuickSight is registered; check that the QuickSight
   service role can assume the Athena workgroup role.
9. For non-AWS ingestion: `aws cloudtrail list-partner-event-sources`
   (deprecated) — or `list-event-data-stores` filtering by
   `EventCategory: non-AWS` — confirm the Partner event source is
   registered and points to the intended EDS.
10. For multi-account ingestion: confirm the management account has
    `AWSServiceRoleForCloudTrail` and any service-linked roles
    enabled.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing
  operation (`create-event-data-store`, `update-event-data-store`,
  `delete-event-data-store`, `start-query`,
  `restore-event-data-store`, `undelete-event-data-store`),
  emit: `CONFIRM: About to <operation> on EDS <eds-id> in account
  <account> region <region>. This will <consequence>. Proceed?
  (yes/no)`. Do NOT execute until the operator confirms.

- **Capture pre-state for rollback.** Before any EDS change:
  `aws cloudtrail get-event-data-store --event-data-store <id>
  --output json > /tmp/<id>-pre-$(date +%s).json`. This is the
  only rollback path — `update-event-data-store` overwrites
  event selectors and retention.

- **Verify KMS key policies, not just IAM.** SSE-KMS EDS require
  the key policy to grant `cloudtrail.amazonaws.com`
  `kms:GenerateDataKey`, `kms:Decrypt`. IAM alone is not
  sufficient.

- **Verify the EDS EventCategory list before queries.** A query
  against an EDS missing the relevant category returns zero rows
  without an error. Always cross-check the categories.

- **Verify organization scope.** Org-scoped EDS can only be created
  by the management account. Member-account queries against an org
  EDS require the management account's permission delegation.

- **Prefer additive changes over destructive ones.** Adding an
  EventCategory to an existing EDS is reversible; deleting an EDS
  is irreversible past 7 days.

- **Validate the SQL before `start-query`.** Run a smoke-test query
  with a tight `eventTime` window and `LIMIT 10` first; only scale
  up once the smoke test returns the expected columns.
