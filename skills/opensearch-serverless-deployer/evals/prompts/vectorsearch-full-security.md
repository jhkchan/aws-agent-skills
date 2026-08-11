# Eval prompt: vectorsearch-full-security

Design a deployment plan for a production OpenSearch Serverless VECTORSEARCH
collection. Emit the standard VERDICT block (COLLECTION, VERDICT,
PRE_CHECKS, STEPS, POST_VERIFY, TYPE, ENCRYPTION, NETWORK, OCU, ACCESS,
AUTH, LIFECYCLE).

Requirements:

- Collection name: prod-vectors
- Type: VECTORSEARCH
- Encryption: customer-managed KMS key
  arn:aws:kms:us-east-1:111111111111:key/abc-123 (SYMMETRIC_DEFAULT)
- Network: VPC-only (vpce-xyz123 in vpc-abc123, subnets subnet-aaa
  subnet-bbb, security group sg-abc123)
- Standby replicas: ENABLED
- OCU floor: 2 indexing + 2 search (4 total, standby doubles to 8)
- Data access: 3 IAM principals
  - arn:aws:iam::111111111111:role/AppRole (admin: CreateCollectionItems, DescribeCollectionItems, UpdateCollectionItems)
  - arn:aws:iam::111111111111:role/SearchRole (read: ReadDocuments, DescribeCollectionItems)
  - arn:aws:iam::111111111111:role/IngestRole (write: WriteDocuments)
- Auth: SAML via IAM Identity Center
  (metadata URL: https://identity-center.amazonaws.com/saml/metadata/abc,
  group attribute: department, session timeout: 60 min)
- Vector: faiss HNSW, dimension 1536, cosinesimil (ef_construction 128, m 24)

Existing-account context: two other collections (prod-search, prod-logs)
exist in the account. The encryption policy prod-encryption already
matches collection/prod-* and references KMS key abc-123 (verified
SYMMETRIC_DEFAULT). The network policy prod-network already matches
collection/prod-* with SourceVPCEs including vpce-xyz123. The operator
holds opensearchserverless:CreateCollection and CreateAccessPolicy
permissions.
