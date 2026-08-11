---
name: opensearch-serverless-deployer
description: >-
  Provisions Amazon OpenSearch Serverless collections with secure defaults —
  collection type selection (SEARCH, TIMESERIES, VECTORSEARCH), encryption
  policy with customer-managed KMS (must exist before collection), network
  policy (public or VPC-only), data lifecycle policy (retention), capacity
  (OCU, min 4 for HA, auto-scaling), standby replicas, SAML / IAM Identity
  Center authentication, data access policies (IAM principals), VPC
  endpoints, vector search (k-NN, faiss, nmslib), semantic search with
  Bedrock embeddings, and flow frameworks. Runs deterministic pre-checks
  (encryption-policy-first ordering, KMS symmetric key, network policy
  precedes collection, OCU minimum, SAML metadata URL), emits create-
  collection CLIs behind a CONFIRM gate, verifies via list-collections.
  Emits READY_TO_DEPLOY | PREREQUISITES_MISSING. Use when provisioning
  OpenSearch Serverless, configuring vector search, or setting up semantic
  search collections.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline plan classification. Live-account
  operations use aws opensearchserverless create-security-policy (encryption,
  network), create-collection, create-vpc-endpoint, create-access-policy,
  update-collection, list-collections, batch-get-collection (AWS CLI v2, SSO
  or key-based credentials).
keywords:
  - OpenSearch Serverless
  - collection
  - VECTORSEARCH
  - SEARCH
  - TIMESERIES
  - OCU
  - OpenSearch Compute Units
  - encryption policy
  - network policy
  - data lifecycle policy
  - access policy
  - KMS
  - VPC endpoint
  - SAML
  - IAM Identity Center
  - k-NN
  - faiss
  - vector search
  - semantic search
  - flow frameworks
  - standby replicas
tags: [opensearch, analytics, deploy, serverless, vector-search, kms, vpc, saml, semantic-search, collection]
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Analytics
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - opensearch
    - analytics
    - deploy
    - serverless
    - vector-search
    - kms
    - vpc
    - saml
    - collection
  dependencies:
    - aws-orchestrator
  keywords:
    - OpenSearch Serverless
    - VECTORSEARCH
    - OCU
    - encryption policy
    - network policy
    - KMS
    - VPC endpoint
    - vector search
    - semantic search
  when_to_use: >-
    Provisioning a new OpenSearch Serverless collection (SEARCH, TIMESERIES,
    or VECTORSEARCH), configuring encryption with customer-managed KMS,
    setting up VPC-only network access, enabling SAML or IAM Identity Center
    authentication, defining data lifecycle policies, sizing OCU capacity,
    deploying vector or semantic search, or wiring flow frameworks.
  activation_triggers:
    - "create OpenSearch Serverless collection"
    - "provision vector search collection"
    - "OpenSearch Serverless with KMS"
    - "OpenSearch Serverless VPC endpoint"
    - "semantic search collection"
    - "k-NN vector index"
    - "OpenSearch Serverless SAML auth"
    - "OCU capacity planning"
    - "flow frameworks OpenSearch"
    - "opensearchserverless create-collection"
  invocation_schema: >-
    Input: either (a) a collection deployment intent (create, update) with
    target collection name, type (SEARCH / TIMESERIES / VECTORSEARCH),
    encryption, network, capacity, access, lifecycle, and optional vector
    config; OR (b) a collection id for live-account update or validation.
    Output: deterministic COLLECTION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY
    block per operation, where VERDICT is one of READY_TO_DEPLOY,
    PREREQUISITES_MISSING.
---

# OpenSearch Serverless Deployer

## What this skill does

Provisions Amazon OpenSearch Serverless collections with secure defaults —
encryption policy created BEFORE the collection (KMS key is immutable
post-creation), network policy preceding collection creation, data access
policy using IAM principals (never resource-based), standby replicas
enabled for HA, OCU floor at 4 (2 indexing + 2 search) for production, and
lifecycle policies for timeseries/vectorsearch retention. Runs deterministic
pre-checks before any state-changing CLI, emits the exact `create-collection`
and `create-security-policy` CLIs behind a CONFIRM gate, and verifies the
collection via `list-collections`. Every plan surfaces the encryption-first
ordering rule, the network-policy-before-collection rule, the data-access-
policy vs resource-policy distinction, and the OCU cost floor.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Verdict thresholds + pre-check priority order + collection type matrix | Before any operation |
| **Mindset** | Why encryption-first ordering matters; immutable collection fields; OCU cost floor | Understanding the deployment model |
| **Pre-flight** | Collection metadata gate — KMS key, VPC subnets, SAML metadata, IAM permissions | Before executing any CLI |
| **Process** | Per-operation planning: encryption, network, lifecycle, collection, VPC endpoint, access | When choosing which operation |
| **STRICT output contract** | Required COLLECTION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY block | Formatting the response |
| **NEVER (top 5)** | Hard rules that prevent common insecure or broken patterns | Review before deploy |
| **Expert heuristic** | Choosing collection type and OCU capacity per use case | Sizing and type selection |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `PREREQUISITES_MISSING` | Any pre-check failed (encryption policy missing or wrong key type, network policy missing, VPC subnets invalid, SAML metadata unreachable, IAM permission missing, collection name collision, standby replicas disabled in production, OCU floor below 4, attempting to change immutable field on update) | List failures, do NOT execute |
| `READY_TO_DEPLOY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence with full collection config, wait for operator yes |

**Priority order for pre-checks (apply in this sequence, all must pass for
READY_TO_DEPLOY):**

1. **Collection name uniqueness** — `list-collections` returns no match (for
   create) or matches exactly one (for update).
2. **Encryption policy exists** — a security policy of type `encryption`
   with a matching pattern exists BEFORE collection creation. Without it,
   the collection uses the AWS-owned key and cannot be changed after.
3. **KMS key is symmetric** — if the encryption policy references a
   customer-managed KMS key, it MUST be `SYMMETRIC_DEFAULT`.
4. **Network policy exists** — a security policy of type `network` covering
   the collection pattern exists BEFORE creation. Without it, the collection
   is unreachable.
5. **Standby replicas** — for production, `StandbyReplicas: ENABLED`. Doubles
   the OCU cost but survives an AZ failure. DISABLED is dev/staging only.
6. **OCU floor** — minimum 2 indexing + 2 search OCUs (4 total) for
   production. Below this, the collection cannot handle concurrency.
7. **VPC subnets** — if VPC access, the VPC ID and subnet IDs resolve and
   security groups exist.
8. **Data access policy** — at least one IAM principal has collection-level
   and document-level grants. Without it, the collection is unreachable.
9. **SAML metadata (if SAML auth)** — the metadata URL or XML is reachable
   and parses as valid SAML 2.0.
10. **Lifecycle policy (timeseries)** — a `lifecycle` policy covering the
    collection pattern exists. Without it, data accumulates indefinitely.

## Mindset

**One-line takeaway:** an OpenSearch Serverless collection is not "an
Elasticsearch cluster that scales itself" — it is a **policy-ordered
deployment** where the encryption and network policies MUST exist BEFORE
the collection, the KMS key choice is immutable post-creation, and the OCU
floor determines both cost and availability.

Three facts make OpenSearch Serverless provisioning different from managed
OpenSearch:

- **Encryption policy MUST exist before collection creation.** The KMS key
  referenced is bound at creation time and CANNOT be changed. If no
  encryption policy matches, OpenSearch Serverless silently uses an AWS-owned
  key — acceptable but opaque (no CloudTrail key usage, no rotation
  visibility). Operators who want customer-managed KMS must create the
  encryption policy FIRST.

- **Network policy MUST exist before collection creation.** A collection
  without a matching network policy is unreachable — neither public nor VPC
  endpoints can connect. Creating the collection first and adding the network
  policy later leaves it unusable until propagation (5-15 minutes).

- **OCU is the cost floor, not the ceiling.** OpenSearch Serverless bills by
  OCU-hour whether idle or busy. Minimum 4 OCUs (2 indexing + 2 search) at
  ~$0.204/OCU-hour = ~$590/month baseline. Standby replicas double it. Sizing
  the floor correctly is the #1 cost control.

## Quick reference — collection type matrix

| Type | Use case | Lifecycle | k-NN |
|---|---|---|---|
| `SEARCH` | Full-text search, catalog, document search | Optional | Limited |
| `TIMESERIES` | Logs, metrics, IoT with time-based retention | Required (retention + storage transition) | No |
| `VECTORSEARCH` | Vector similarity, semantic search, RAG | Optional (size-based) | Yes (primary use case) |

## Pre-flight: collection deployment gate

Before producing the deployment plan, validate the input specification.
Several requirements **block deployment**.

**Live-account pre-flight checks (skip if offline architecture plan):**
1. Verify IAM permissions for `opensearchserverless:CreateCollection`,
   `CreateSecurityPolicy`, `CreateAccessPolicy`, `CreateVpcEndpoint`.
2. Verify the encryption security policy exists:
   `aws opensearchserverless list-security-policies --type encryption`
3. Verify the network security policy exists:
   `aws opensearchserverless list-security-policies --type network`
4. For VPC access, verify VPC ID, subnet IDs, security group IDs resolve.
5. For SAML auth, verify the SAML metadata URL is reachable.
6. Verify KMS key (if customer-managed) is `SYMMETRIC_DEFAULT`:
   `aws kms describe-key --key-id <id> --query 'KeyMetadata.KeySpec'`

**If the deployment spec is incomplete**, output:

```text
COLLECTION: <name-or-unknown>
VERDICT: PREREQUISITES_MISSING
REASON: Deployment specification is missing required fields (<list>).
REQUIRED:
  - collection_type (SEARCH | TIMESERIES | VECTORSEARCH)
  - encryption (aws-owned-key | customer-managed-kms:arn)
  - network (public | vpc:vpc-id:subnet-ids:security-group-ids)
  - ocu_floor (minimum 4 for production: 2 indexing + 2 search)
  - standby_replicas (ENABLED for production HA)
  - access_principals (IAM role ARNs with data access grants)
```

## Process — Architecture planning (apply in order)

### Step 0: Expert knowledge — non-obvious behaviors

- **Encryption policy is matched by collection name pattern.** The policy
  `Rules` array has `ResourceType: collection` and `Resource:
  ["collection/<pattern>"]`. The collection name must match at creation.
- **KMS key choice is IMMUTABLE.** Once created, the key cannot be changed.
  To change it, delete the collection (data loss) and recreate.
- **Network policy has two access types: public and vpc.** A single policy
  can include both — public for the collection endpoint, VPC for dashboards.
- **Data access policy uses IAM principals, NOT resource-based policies.**
  OpenSearch Serverless does NOT support resource-based policies. The
  collection creator does NOT automatically get access — a data access
  policy MUST be created.
- **VPC endpoint is a separate resource.** After collection creation,
  `create-vpc-endpoint` connects the VPC. Takes 5-15 minutes. The security
  group must allow inbound 443 from the application subnet.
- **Standby replicas double the OCU cost.** `StandbyReplicas: ENABLED`
  maintains a warm replica in a second AZ. Required for HA production.
- **OCU auto-scaling is workload-driven.** Scales up at 70% CPU/memory for
  5 min, down at 30% for 30 min. Floor never goes below configured minimum.
- **Collection creation takes 15-30 minutes.** CREATING → ACTIVE. Do not
  emit POST_VERIFY checks expecting immediate ACTIVE.
- **Flow frameworks (2024-2025):** ML model provisioning templates that
  automate connector setup, model registration, inference pipelines.
- **Semantic search requires an embeddings connector.** For true semantic
  search, OpenSearch Serverless must call an embeddings model (Bedrock
  Titan). The connector role must have `bedrock:InvokeModel`.

### Step 1: Collection type selection

| Type | When to use | Notes |
|---|---|---|
| `SEARCH` | Full-text, catalog, document search | Standard indexes; optional lifecycle |
| `TIMESERIES` | Logs, metrics with retention | Time-partitioned; lifecycle REQUIRED |
| `VECTORSEARCH` | Semantic search, RAG, recommendations | k-NN (faiss/nmslib); lifecycle optional |

**Anti-pattern:** NEVER use `SEARCH` for time-based log retention. Without
lifecycle policies, logs accumulate indefinitely. Use `TIMESERIES`.

### Step 2: Encryption policy (create BEFORE collection)

```bash
aws opensearchserverless create-security-policy \
  --name prod-encryption --type encryption \
  --policy '{"Rules":[{"ResourceType":"collection","Resource":["collection/prod-*"]}],"KmsKeyArn":"arn:aws:kms:us-east-1:111111111111:key/abc-123"}'
```

**KMS key requirements:**
- MUST be `SYMMETRIC_DEFAULT` (no asymmetric keys).
- Key policy MUST grant `kms:Decrypt`, `kms:DescribeKey`, `kms:CreateGrant`
  to `opensearch-serverless.amazonaws.com`.
- For AWS-owned key, omit `KmsKeyArn`.

### Step 3: Network policy (create BEFORE collection)

```bash
aws opensearchserverless create-security-policy \
  --name prod-network --type network \
  --policy '{"Rules":[{"ResourceType":"collection","Resource":["collection/prod-*"]}],"AllowFromPublic":true}'
```

For VPC-only: replace `AllowFromPublic` with `"SourceVPCEs": ["vpce-abc123"]`.

### Step 4: Data lifecycle policy (TIMESERIES)

```bash
aws opensearchserverless create-lifecycle-policy \
  --name prod-lifecycle --type retention \
  --policy '{"Rules":[{"ResourceType":"index","Resource":{"index":"prod-logs-*"},"MinIndexRetention":"7d","MaxIndexRetention":"30d"}]}'
```

### Step 5: Collection creation

```bash
aws opensearchserverless create-collection \
  --name prod-vectors --type VECTORSEARCH \
  --description "Production vector search for RAG" \
  --standby-replicas ENABLED
```

Creation takes 15-30 minutes (CREATING → ACTIVE). Default OCU floor is 4
(2 indexing + 2 search).

### Step 6: VPC endpoint (if VPC network)

```bash
aws opensearchserverless create-vpc-endpoint \
  --name prod-vpce --vpc-id vpc-abc123 \
  --subnet-ids subnet-aaa subnet-bbb \
  --security-group-ids sg-abc123 \
  --collection-endpoints <endpoint-from-step-5>
```

### Step 7: Data access policy (IAM principals)

```bash
aws opensearchserverless create-access-policy \
  --name prod-access --type data \
  --policy '[{"Permission":["aoss:CreateCollectionItems","aoss:DescribeCollectionItems"],"Principal":["arn:aws:iam::111111111111:role/AppRole"]}]'
```

The collection creator does NOT automatically get access. A data access
policy MUST be created.

### Step 8: SAML / IAM Identity Center authentication

```bash
aws opensearchserverless update-collection \
  --id <collection-id> \
  --saml-options '{"Metadata":{"URL":"https://identity-center.amazonaws.com/saml/metadata/abc"},"GroupAttribute":"department","SessionTimeout":60}'
```

### Step 9: Capacity configuration (OCU)

```bash
aws opensearchserverless update-collection \
  --id <collection-id> \
  --capacity '{"CapacityLimits":{"MaxIndexingCapacityInOCU":8,"MaxSearchCapacityInOCU":8}}'
```

### Step 10: Vector search and semantic search

For VECTORSEARCH collections, the application creates the k-NN index:

```json
{
  "settings": {"index": {"knn": true}},
  "mappings": {"properties": {"embedding": {
    "type": "knn_vector", "dimension": 1536,
    "method": {"name": "hnsw", "space_type": "cosinesimil", "engine": "faiss",
               "parameters": {"ef_construction": 128, "m": 24}}
  }}}
}
```

**Engine:** `faiss` (recommended; HNSW + IVF) or `nmslib` (legacy).

**Semantic search:** register an ML connector to Bedrock Titan Embeddings
via ML Commons, then create a neural search pipeline that calls the model
at ingest and query time.

## Output format (per collection deployment plan)

```text
COLLECTION: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
ARCHITECTURE:
  Type: <SEARCH | TIMESERIES | VECTORSEARCH>
  Encryption: <customer-managed KMS ARN | aws-owned-key>
  Network: <public | VPC vpce-xxx>
  Standby replicas: <ENABLED | DISABLED>
  OCU floor: <indexing> indexing + <search> search = <total>
  Access: <IAM principal count> principals via data access policy
  Auth: <SAML | IAM-only>
  Lifecycle: <retention rules | none>
  Vector: <k-NN engine + dimension | N/A>
CHECKLIST:
  [x] Encryption policy exists and references symmetric KMS key
  [x] Network policy exists and covers collection pattern
  [x] Collection type matches use case
  [x] Standby replicas ENABLED for production HA
  [x] OCU floor >= 4 (2 indexing + 2 search)
  [x] Data access policy with IAM principals
  [x] VPC endpoint configured (if VPC network)
  [x] SAML metadata reachable (if SAML auth)
  [x] Lifecycle policy for retention (TIMESERIES required)
FINDINGS:
  - [INFO] Estimated monthly cost: OCU floor <N> x $0.204/hr x 720 = $<X>
  - [WARN] Standby replicas ENABLED doubles OCU cost
DEPLOY_COMMANDS:
  <ordered list of aws opensearchserverless commands>
```

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble:

```text
COLLECTION: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
TARGET: <name> (collection-id: <id> for updates)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. CONFIRM: About to <operation> collection <name> in account <account> region <region>. This will <consequence>. Proceed? (yes/no)
  2. <exact CLI command — no placeholders>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
TYPE: SEARCH | TIMESERIES | VECTORSEARCH
ENCRYPTION: <KMS ARN | aws-owned-key>
NETWORK: <public | VPC vpce-xxx>
OCU: <indexing> indexing + <search> search (<standby> standby)
ACCESS: <count> IAM principals
AUTH: <SAML | IAM-only>
LIFECYCLE: <retention rules | none>
NOTES: <security posture, cost estimate, capacity caveats>
```

### FORBIDDEN output patterns

- NEVER start with "Let me analyze…" — the VERDICT block is the FIRST line.
- NEVER use lowercase verdict values — emit `READY_TO_DEPLOY` or
  `PREREQUISITES_MISSING`.
- NEVER omit PRE_CHECKS — every pre-check must appear with `[PASS]` or
  `[FAIL]` and a specific reason.
- NEVER emit placeholder values in a READY_TO_DEPLOY plan.
- NEVER omit the CONFIRM gate as the first STEPS entry.
- NEVER claim success without verifying ACTIVE via `batch-get-collection`.
- NEVER change CLI step order — encryption first, network second, collection
  third.
- NEVER silently allow AWS-owned key for compliance workloads — flag as
  [WARN].

### Perfect example output

```text
COLLECTION: prod-vectors
VERDICT: READY_TO_DEPLOY
TARGET: prod-vectors
PRE_CHECKS:
  - [PASS] Collection name unique
  - [PASS] Encryption policy prod-encryption exists, references KMS abc-123
  - [PASS] KMS key abc-123 is SYMMETRIC_DEFAULT
  - [PASS] Network policy prod-network exists, covers collection/prod-*
  - [PASS] VPC subnets resolve in vpc-abc123
  - [PASS] Standby replicas ENABLED for production HA
  - [PASS] OCU floor 4 (2 indexing + 2 search)
  - [PASS] Data access policy prod-access has 3 IAM principals
  - [PASS] SAML metadata URL reachable
  - [PASS] IAM principal holds opensearchserverless:CreateCollection
STEPS:
  1. CONFIRM: About to create-collection prod-vectors in account 111111111111 region us-east-1. VECTORSEARCH with KMS, VPC, SAML, standby replicas. Estimated monthly cost: $1175 (4 OCU x 2 standby x $0.204/hr x 720). Takes 15-30 min. Proceed? (yes/no)
  2. aws opensearchserverless create-security-policy --name prod-encryption --type encryption --policy '{"Rules":[{"ResourceType":"collection","Resource":["collection/prod-*"]}],"KmsKeyArn":"arn:aws:kms:us-east-1:111111111111:key/abc-123"}'
  3. aws opensearchserverless create-security-policy --name prod-network --type network --policy '{"Rules":[{"ResourceType":"collection","Resource":["collection/prod-*"]}],"SourceVPCEs":["vpce-xyz123"]}'
  4. aws opensearchserverless create-collection --name prod-vectors --type VECTORSEARCH --description "Production vector search for RAG" --standby-replicas ENABLED
  5. aws opensearchserverless create-access-policy --name prod-access --type data --policy '[{"Permission":["aoss:CreateCollectionItems","aoss:DescribeCollectionItems"],"Principal":["arn:aws:iam::111111111111:role/AppRole"]}]'
  6. aws opensearchserverless create-vpc-endpoint --name prod-vpce --vpc-id vpc-abc123 --subnet-ids subnet-aaa subnet-bbb --security-group-ids sg-abc123 --collection-endpoints <endpoint-from-step-4>
POST_VERIFY:
  - (pending execution)
  - batch-get-collection returns status=ACTIVE (wait 15-30 min)
  - get-security-policy returns prod-encryption with KMS abc-123
TYPE: VECTORSEARCH
ENCRYPTION: arn:aws:kms:us-east-1:111111111111:key/abc-123
NETWORK: VPC vpce-xyz123
OCU: 2 indexing + 2 search (standby doubles to 8 effective)
ACCESS: 3 IAM principals
AUTH: SAML via IAM Identity Center
LIFECYCLE: none (VECTORSEARCH)
NOTES:
  - KMS key is immutable post-creation.
  - Standby replicas double OCU cost ($1175/mo vs $588/mo).
  - Data access policy required — creator gets NO default access.
```

## Verification commands (run after deployment)

```bash
# Verify collection is ACTIVE
aws opensearchserverless batch-get-collection --ids <id> --query 'collections[0].status'
# Verify encryption policy
aws opensearchserverless get-security-policy --name prod-encryption --type encryption
# Verify network policy
aws opensearchserverless get-security-policy --name prod-network --type network
# Verify VPC endpoint
aws opensearchserverless list-vpc-endpoints --vpc-endpoint-id vpce-xyz123 --query 'vpcEndpointSummaries[0].status'
# Verify KMS symmetric
aws kms describe-key --key-id abc-123 --query 'KeyMetadata.KeySpec'
```

## Edge-case handling

- **Encryption policy created after collection.** PREREQUISITES_MISSING. The
  collection is using an AWS-owned key. Cannot be changed retroactively.
- **Network policy missing.** PREREQUISITES_MISSING. Collection unreachable.
- **KMS key is asymmetric.** PREREQUISITES_MISSING. Requires
  `SYMMETRIC_DEFAULT`.
- **VPC subnet not found.** PREREQUISITES_MISSING.
- **SAML metadata URL unreachable.** PREREQUISITES_MISSING.
- **Data access policy missing.** PREREQUISITES_MISSING. Creator has no
  access without it.

## NEVER (top 5)

1. **NEVER create the collection before the encryption policy.** The KMS key
   is IMMUTABLE post-creation. Without a matching encryption policy, the
   collection silently uses an AWS-owned key with no key visibility. Create
   the encryption policy FIRST, always.

2. **NEVER create the collection before the network policy.** Without a
   matching network policy, the collection endpoint is unreachable — neither
   public nor VPC. Takes 5-15 min to propagate after creation.

3. **NEVER omit the data access policy.** OpenSearch Serverless uses IAM
   principals via data access policies, NOT resource-based policies. The
   creator gets NO default access. Always emit `create-access-policy`.

4. **NEVER use an asymmetric KMS key.** Requires `SYMMETRIC_DEFAULT`.
   Asymmetric keys fail with an opaque error. Verify via
   `kms describe-key --query 'KeyMetadata.KeySpec'`.

5. **NEVER disable standby replicas for production.** Without standby, an AZ
   failure causes complete downtime. ENABLED doubles OCU cost but is required
   for HA. DISABLED is dev/staging only.

## Expert heuristic: choosing collection type and OCU capacity

```
Workload pattern
   ├─ Vector similarity / semantic search / RAG?
   │    └─ VECTORSEARCH (faiss HNSW, cosinesimil)
   │         Dimension: match embeddings model (1536 for Bedrock Titan)
   │         OCU: 2 indexing + 2 search floor
   │
   ├─ Time-series logs / metrics with retention?
   │    └─ TIMESERIES (time-partitioned, lifecycle REQUIRED)
   │         OCU: 2 indexing + 2 search floor
   │         ISM: managed indexes with rollover
   │
   ├─ Full-text search / catalog / documents?
   │    └─ SEARCH (standard indexes, optional lifecycle)
   │         OCU: 2 indexing + 2 search floor
   │
   └─ Hybrid (full-text + vector)?
        └─ VECTORSEARCH with hybrid query
             OCU: 4 indexing + 4 search floor
```

**OCU sizing rules:**
- **Floor:** 2 indexing + 2 search = 4 OCU minimum. Handles ~1000 docs/sec
  ingest, ~100 queries/sec.
- **Search scaling:** +1 search OCU per ~50 additional queries/sec.
- **Indexing scaling:** +1 indexing OCU per ~500 additional docs/sec.
- **Standby:** doubles effective OCU count and cost.

**Cost estimation (us-east-1):**
- 4 OCU (no standby) = 4 x $0.204 x 720 = $588/month
- 4 OCU (with standby) = 8 x $0.204 x 720 = $1175/month
- Storage: $0.024/GB-month (included up to ~120 GB/OCU)

ALWAYS emit the cost estimate in FINDINGS. OCU is the dominant cost.

## Recent AWS features (2024-2026)

- **Vector search collections (2023-2024):** `VECTORSEARCH` with k-NN (faiss,
  nmslib) for RAG, semantic search, recommendations. HNSW algorithm.
- **Semantic search with Bedrock (2024-2025):** ML Commons connector to
  Bedrock Titan Embeddings enables neural search. Requires
  `bedrock:InvokeModel`.
- **Flow frameworks (2024-2025):** JSON templates automating ML model
  provisioning — connector, model, pipeline. Via
  `_plugins/_flow_frameworks/workflow` API.
- **IAM Identity Center SAML (2024-2025):** native SAML app type. Metadata
  URL registered via `update-collection --saml-options`.
- **Data lifecycle policies (2024):** `create-lifecycle-policy` with
  `MinIndexRetention`, `MaxIndexRetention`, `NoSnapshot`.
- **Standby replicas GA (2024):** `StandbyReplicas: ENABLED` with automated
  AZ failover.
- **VPC endpoint private DNS (2025):** collection endpoint resolves via
  Route 53 resolver without custom DNS.

## AWS documentation

- **OpenSearch Serverless Developer Guide** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless.html
- **Encryption policies** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-encryption.html
- **Network policies** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-network.html
- **Data access policies** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-data-access.html
- **Vector search** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-vector-search.html
- **Capacity and OCU** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-capacity.html
- **SAML authentication** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-saml.html
- **CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/opensearchserverless/

## Domain

AWS CloudOps / OpenSearch Serverless Analytics & Vector Search Provisioning.
