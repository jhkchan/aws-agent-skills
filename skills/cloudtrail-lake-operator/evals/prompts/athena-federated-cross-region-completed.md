# Eval prompt: athena-federated-cross-region-completed

Produce the COMPLETED post-verification form for an Athena-federated
cross-Region CloudTrail Lake JOIN query that succeeded. Emit the
standard VERDICT block.

Operation: federate-via-athena
EDS us-east-1: arn:aws:cloudtrail:us-east-1:111111111111:event-data-store/eds-us-east-1
EDS eu-west-1: arn:aws:cloudtrail:eu-west-1:111111111111:event-data-store/eds-eu-west-1
Athena workgroup: gov-analytics

```json
{
  "FederationPreChecks": {
    "ConnectorDeployed": ["us-east-1", "eu-west-1"],
    "LakeFormationGrants": "verified on connector Lambda roles for both EDS",
    "WorkgroupRolePermissions": "cloudtrail:StartQuery, GetQuery, GetQueryResults on both EDS",
    "KmsDecryptGrants": "verified for both KMS keys"
  },
  "Execution": {
    "QueryExecutionId": "athena-exec-001",
    "SQL": "SELECT us.userIdentity.accountId, us.eventName, us.eventTime AS us_time, eu.eventTime AS eu_time FROM lambda:cloudtraillake_us_east_1.eds-us-east-1 us JOIN lambda:cloudtraillake_eu_west_1.eds-eu-west-1 eu ON us.userIdentity.sessionId = eu.userIdentity.sessionId WHERE us.eventTime >= date_add('day', -1, now()) AND eu.eventTime >= date_add('day', -1, now()) AND us.eventName = 'AssumeRole' ORDER BY us.eventTime DESC LIMIT 1000"
  },
  "AthenaQueryExecution": {
    "State": "SUCCEEDED",
    "DataScannedInBytes": 4200000000,
    "ResultRows": 842,
    "OutputLocation": "s3://athena-results-111111111111/gov/athena-exec-001.csv"
  },
  "LakeUnderlyingQuery": {
    "Region": "us-east-1",
    "QueryStatus": "FINISHED",
    "BytesScanned": 3900000000
  },
  "SpotCheck": {
    "RowsInspected": 3,
    "FieldsMatched": ["accountId", "eventName", "eventTime"]
  }
}
```
