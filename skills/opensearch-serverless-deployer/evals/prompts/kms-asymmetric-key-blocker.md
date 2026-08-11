# Eval prompt: kms-asymmetric-key-blocker

Design a deployment plan for an OpenSearch Serverless VECTORSEARCH
collection for a semantic search application. Emit the standard VERDICT
block.

Requirements:

- Collection name: prod-semantic-search
- Type: VECTORSEARCH
- Encryption: customer-managed KMS key
  arn:aws:kms:us-east-1:111111111111:key/def-456
- Network: VPC-only (vpce-abc456 in vpc-abc123)
- Standby replicas: ENABLED
- OCU floor: 2 indexing + 2 search
- Data access: IAM principals for the application role
- Vector: faiss HNSW, dimension 1536

Existing-account context: the encryption policy prod-encryption-semantic
exists and matches collection/prod-semantic-search, referencing KMS key
def-456. However, KMS key def-456 was created with KeySpec RSA_2048
(asymmetric) for a different application (digital signing). The operator
assumed any KMS key works with OpenSearch Serverless. The key policy
grants the necessary permissions to opensearch-serverless.amazonaws.com.

The operator wants to proceed with deployment immediately.
