# Eval prompt: missing-encryption-policy

Design a deployment plan for an OpenSearch Serverless SEARCH collection
for a product catalog search application. Emit the standard VERDICT block.

Requirements:

- Collection name: prod-search
- Type: SEARCH
- Encryption: customer-managed KMS key
  arn:aws:kms:us-east-1:111111111111:key/abc-123 (SYMMETRIC_DEFAULT)
- Network: public (search API accessed via the public endpoint with IAM
  auth)
- Standby replicas: ENABLED
- OCU floor: 2 indexing + 2 search
- Data access: IAM principals for the search application role

Existing-account context: this is a new account with no existing
OpenSearch Serverless collections. The operator has not created any
security policies yet. `aws opensearchserverless list-security-policies
--type encryption` returns an empty list. `aws opensearchserverless
list-security-policies --type network` also returns empty.

The operator wants to use customer-managed KMS key abc-123 for encryption
and expects the encryption policy to be created as part of the deployment
plan, but has not explicitly stated whether the encryption policy must
exist before the collection.
