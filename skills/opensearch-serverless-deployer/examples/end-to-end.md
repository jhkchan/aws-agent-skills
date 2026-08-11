# End-to-end usage scenario: opensearch-serverless-deployer

A walkthrough showing the skill producing a deployment plan for a
production OpenSearch Serverless VECTORSEARCH collection with
customer-managed KMS, VPC endpoint, SAML authentication, standby
replicas, and a Bedrock-powered semantic search pipeline. Demonstrates
the READY_TO_DEPLOY verdict, pre-check list, and ordered deploy-command
sequence.

## Input (user prompt)

> Provision an OpenSearch Serverless collection for our RAG application.
> It needs to be VECTORSEARCH type with customer-managed KMS key
> `abc-123` (symmetric). The collection should be VPC-only accessible via
> `vpce-xyz123` in `vpc-abc123` (subnets `subnet-aaa`, `subnet-bbb`,
> security group `sg-abc123`). Enable standby replicas for production HA.
> Use SAML via IAM Identity Center for dashboard auth (metadata URL
> `https://identity-center.amazonaws.com/saml/metadata/abc`, group
> attribute `department`). The application role `AppRole` needs admin
> access and `SearchRole` needs read-only. Vectors are 1536-dimensional
> (Bedrock Titan Embeddings v2) using faiss HNSW with cosine similarity.

## Expected behavior

1. **Pre-flight:** The skill validates the spec — collection name unique,
   encryption policy exists and references symmetric KMS key, network
   policy exists, VPC subnets resolve, SAML metadata URL reachable, IAM
   permissions present.
2. **Encryption:** Encryption policy `prod-encryption` already exists
   matching `collection/prod-*` with KMS key `abc-123`. No action needed
   — verify via `get-security-policy`.
3. **Network:** Network policy `prod-network` already exists with VPC
   endpoint `vpce-xyz123`. No action needed — verify.
4. **Collection:** Plans `create-collection` with `VECTORSEARCH` type,
   standby replicas ENABLED.
5. **Access:** Plans `create-access-policy` with AppRole (admin) and
   SearchRole (read-only).
6. **VPC endpoint:** Plans `create-vpc-endpoint` in `vpc-abc123`.
7. **SAML:** Plans `update-collection --saml-options` with IAM Identity
   Center metadata.
8. **Verdict:** READY_TO_DEPLOY — all pre-checks pass.

## Expected output

```text
COLLECTION: prod-vectors
VERDICT: READY_TO_DEPLOY
TARGET: prod-vectors
PRE_CHECKS:
  - [PASS] Collection name unique (no collision in list-collections)
  - [PASS] Encryption policy prod-encryption exists, references KMS abc-123
  - [PASS] KMS key abc-123 is SYMMETRIC_DEFAULT
  - [PASS] Network policy prod-network exists, covers collection/prod-*
  - [PASS] VPC subnets subnet-aaa, subnet-bbb resolve in vpc-abc123
  - [PASS] Standby replicas ENABLED for production HA
  - [PASS] OCU floor 4 (2 indexing + 2 search)
  - [PASS] Data access policy plan has 2 IAM principals
  - [PASS] SAML metadata URL reachable
  - [PASS] IAM principal holds opensearchserverless:CreateCollection
STEPS:
  1. CONFIRM: About to create-collection prod-vectors in account 111111111111 region us-east-1. VECTORSEARCH with KMS, VPC, SAML, standby replicas. Estimated monthly cost: $1175 (4 OCU x 2 standby x $0.204/hr x 720). Takes 15-30 min. Proceed? (yes/no)
  2. aws opensearchserverless create-collection --name prod-vectors --type VECTORSEARCH --description "Production vector search for RAG" --standby-replicas ENABLED
  3. aws opensearchserverless create-access-policy --name prod-access --type data --policy '[{"Permission":["aoss:CreateCollectionItems","aoss:DescribeCollectionItems","aoss:UpdateCollectionItems"],"Principal":["arn:aws:iam::111111111111:role/AppRole"]},{"Permission":["aoss:ReadDocuments","aoss:DescribeCollectionItems"],"Principal":["arn:aws:iam::111111111111:role/SearchRole"]}]'
  4. aws opensearchserverless create-vpc-endpoint --name prod-vpce --vpc-id vpc-abc123 --subnet-ids subnet-aaa subnet-bbb --security-group-ids sg-abc123 --collection-endpoints <endpoint-from-step-2>
  5. aws opensearchserverless update-collection --id <id-from-step-2> --saml-options '{"Metadata":{"URL":"https://identity-center.amazonaws.com/saml/metadata/abc"},"GroupAttribute":"department","SessionTimeout":60}'
POST_VERIFY:
  - (pending execution)
  - batch-get-collection returns status=ACTIVE (wait 15-30 min)
  - get-security-policy returns prod-encryption with KMS abc-123
  - list-vpc-endpoints returns prod-vpce status=AVAILABLE
TYPE: VECTORSEARCH
ENCRYPTION: arn:aws:kms:us-east-1:111111111111:key/abc-123
NETWORK: VPC vpce-xyz123
OCU: 2 indexing + 2 search (standby doubles to 8 effective)
ACCESS: 2 IAM principals
AUTH: SAML via IAM Identity Center
LIFECYCLE: none (VECTORSEARCH)
NOTES:
  - KMS key is immutable post-creation. Verify before deploy.
  - Standby replicas double OCU cost ($1175/mo vs $588/mo without standby).
  - Vector dimension 1536 matches Bedrock Titan Embeddings v2.
  - Data access policy required — creator gets NO default access.
```

## Post-deployment verification

After running the deploy commands, verify the collection is correctly
provisioned:

```bash
# Verify collection is ACTIVE (wait 15-30 min)
aws opensearchserverless batch-get-collection \
  --ids <collection-id> \
  --query 'collections[0].status'
# Expect: "ACTIVE"

# Verify encryption policy references correct KMS key
aws opensearchserverless get-security-policy \
  --name prod-encryption --type encryption \
  --query 'securityPolicy.policy' | jq '.KmsKeyArn'
# Expect: arn:aws:kms:us-east-1:111111111111:key/abc-123

# Verify VPC endpoint is AVAILABLE
aws opensearchserverless list-vpc-endpoints \
  --vpc-endpoint-id vpce-xyz123 \
  --query 'vpcEndpointSummaries[0].status'
# Expect: "AVAILABLE"

# Verify data access policy has both principals
aws opensearchserverless get-access-policy \
  --name prod-access --type data \
  --query 'accessPolicy.policy' | jq '. | length'
# Expect: 2

# Test document indexing (requires data access policy in place)
curl -X PUT "https://<collection-endpoint>/test-index/_doc/1" \
  -H "Content-Type: application/json" \
  -d '{"content": "hello world", "embedding": [0.1, 0.2, ...]}'
# Expect: 201 Created
```

## Common pitfalls to verify after deployment

1. **Encryption policy created AFTER collection.** If the collection was
   created before the encryption policy, it silently uses an AWS-owned
   key. The KMS key cannot be changed retroactively. Delete and recreate
   with the encryption policy in place first.
2. **Data access policy missing.** The collection creator does NOT
   automatically get access. Without a data access policy, no one can
   index or query documents. Verify the policy exists and includes the
   creator's IAM role.
3. **VPC endpoint security group.** The security group on the VPC
   endpoint must allow inbound 443 from the application subnet. A
   misconfigured security group blocks all traffic.
4. **SAML metadata URL reachable.** If the metadata URL is behind a
   firewall or requires authentication, OpenSearch Serverless cannot
   fetch it. For IAM Identity Center, verify the application SAML
   metadata URL is publicly reachable.
5. **Vector dimension mismatch.** The index mapping `dimension` must
   match the embeddings model output. Bedrock Titan v2 produces 1536
   dimensions by default. A mismatch causes indexing errors at the
   application level.
