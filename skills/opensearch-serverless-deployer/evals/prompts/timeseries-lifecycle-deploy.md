# Eval prompt: timeseries-lifecycle-deploy

Design a deployment plan for an OpenSearch Serverless TIMESERIES collection
for application log analytics. Emit the standard VERDICT block.

Requirements:

- Collection name: prod-logs
- Type: TIMESERIES
- Encryption: AWS-owned key (acceptable — logs are non-compliance data,
  no KMS visibility needed)
- Network: public (internal application will access the endpoint via IAM
  auth; no VPC endpoint required)
- Standby replicas: ENABLED (production HA — logs are critical for
  debugging)
- OCU floor: 2 indexing + 2 search (4 total)
- Data access: 2 IAM principals
  - arn:aws:iam::111111111111:role/IngestRole (write: WriteDocuments)
  - arn:aws:iam::111111111111:role/QueryRole (read: ReadDocuments, DescribeCollectionItems)
- Lifecycle: MinIndexRetention 7d, MaxIndexRetention 30d, index pattern
  prod-logs-* (NoSnapshot: false — snapshots required for audit)
- Auth: IAM-only (no SAML — logs accessed programmatically)

Existing-account context: no existing encryption policy for prod-logs
(AWS-owned key means the policy just documents intent). The network
policy prod-network-public matches collection/prod-logs-* with
AllowFromPublic: true. The operator holds all required permissions.
