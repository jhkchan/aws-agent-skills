---
description: Provision a production-grade OpenSearch Serverless collection with encryption, network, lifecycle, data access, SAML, VPC endpoint, and vector search.
nl_triggers:
  - "create OpenSearch Serverless collection"
  - "provision vector search collection"
  - "OpenSearch Serverless with KMS"
  - "OpenSearch Serverless VPC endpoint"
  - "semantic search collection"
  - "k-NN vector index"
  - "OpenSearch Serverless SAML auth"
  - "OpenSearch Serverless IAM Identity Center"
  - "OCU capacity planning"
  - "OpenSearch Serverless lifecycle policy"
  - "flow frameworks OpenSearch"
  - "TIMESERIES collection"
  - "VECTORSEARCH collection"
  - "opensearchserverless create-collection"
routes_to: opensearch-serverless-deployer
---

# /aws:deploy-opensearch-serverless

Activate the `opensearch-serverless-deployer` skill and produce a deployment
plan for a production-grade Amazon OpenSearch Serverless collection.

## What it does

Reads a deployment specification (collection type, encryption, network,
capacity, access, lifecycle, vector/semantic search config) and produces
an ordered deployment plan with:

1. Pre-flight specification gate — validates collection type (SEARCH /
   TIMESERIES / VECTORSEARCH), encryption requirement (AWS-owned key vs
   customer-managed KMS), network requirement (public vs VPC). Blocks
   deployment (PREREQUISITES_MISSING) on missing fields or incompatible
   combinations (asymmetric KMS key, missing encryption/network policy).
2. Encryption policy — create BEFORE collection. KMS key MUST be
   SYMMETRIC_DEFAULT. Immutable post-creation.
3. Network policy — create BEFORE collection. Public or VPC-only.
4. Lifecycle policy — TIMESERIES collections require retention rules
   (MinIndexRetention, MaxIndexRetention).
5. Collection creation — type selection, standby replicas (ENABLED for
   production HA), OCU floor (minimum 4: 2 indexing + 2 search).
6. Data access policy — IAM principals with collection-level and
   document-level permissions. Creator does NOT get default access.
7. VPC endpoint — for VPC network access. Takes 5-15 minutes.
8. SAML / IAM Identity Center — metadata URL, group attribute, session
   timeout.
9. Capacity configuration — OCU floor and auto-scaling ceiling.
10. Vector search — k-NN index mapping (faiss/nmslib, HNSW, dimension).
11. Semantic search — Bedrock embeddings connector via ML Commons, neural
    search pipeline, flow frameworks.

Emits a deterministic deployment plan per collection:

```text
COLLECTION: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
PRE_CHECKS:
  - [PASS] <check>
  - [FAIL] <check> — <reason>
STEPS:
  1. CONFIRM: About to <operation> collection <name>...
  2. <exact CLI command>
POST_VERIFY:
  - [PASS] <verification>
TYPE: SEARCH | TIMESERIES | VECTORSEARCH
ENCRYPTION: <KMS ARN | aws-owned-key>
NETWORK: <public | VPC vpce-xxx>
OCU: <indexing> + <search> (<standby>)
...
```

## When to invoke

Provide a deployment spec and ask any of:

- "create an OpenSearch Serverless collection"
- "provision a vector search collection for RAG"
- "set up OpenSearch Serverless with customer-managed KMS"
- "configure VPC-only access for OpenSearch Serverless"
- "enable SAML auth for OpenSearch Serverless dashboards"
- "plan OCU capacity for a vector search workload"
- "set up semantic search with Bedrock embeddings"

A bare collection name + type + "deploy" also routes here via the
orchestrator.

## Inputs

- **Required:** collection_type (SEARCH | TIMESERIES | VECTORSEARCH),
  encryption (aws-owned-key | customer-managed-kms:arn), network (public
  | vpc:vpc-id:subnet-ids:sg-ids), ocu_floor (minimum 4 for production),
  standby_replicas (ENABLED for production), access_principals (IAM role
  ARNs with data access grants).
- **Optional:** saml_metadata_url, saml_group_attribute, lifecycle_policy
  (for TIMESERIES), vector_config (engine, dimension, space_type),
  semantic_search_config (embeddings model, connector role).

## Outputs

- One VERDICT block per collection (READY_TO_DEPLOY or
  PREREQUISITES_MISSING).
- PRE_CHECKS with all validation checks ([PASS] or [FAIL]).
- STEPS with ordered `aws opensearchserverless` commands (encryption
  policy first, network second, collection third).
- POST_VERIFY with verification commands.
- Architecture summary (TYPE, ENCRYPTION, NETWORK, OCU, ACCESS, AUTH,
  LIFECYCLE).
- Cost estimate (OCU floor x $0.204/hr x 720, doubled if standby enabled).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 1 Deploy specialist for OpenSearch Serverless).
- `/aws:audit-opensearch-*` for post-deployment security auditing
  (encryption posture, network exposure, access policy coverage).
