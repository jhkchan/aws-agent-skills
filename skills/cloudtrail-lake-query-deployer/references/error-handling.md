# Error Handling — cloudtrail-lake-query-deployer

## Error handling

### Query returns no results
- The time range may not overlap with ingested events. Check EDS
  ingestion status. Verify the event type (management vs data events
  are in different EDS).

### Query cost is unexpectedly high
- The time range is too broad. Narrow it. Check the bytes scanned
  metric via `describe-query`.

### Data protection not masking PII
- The data protection policy may not include the correct identifier.
  Check the identifiers list. Some fields may not match the expected
  pattern.

### Multi-account EDS not ingesting from member accounts
- Organizations integration may not be enabled. Verify the management
  account has the correct delegated administrator configuration.

### EDS creation fails
- IAM permissions for `cloudtrail:CreateEventDataStore` may be
  missing. Verify the service-linked role exists.
