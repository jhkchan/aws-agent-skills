# Advanced Patterns — OpenSearch Serverless Deployer
Edge-case catalogs, expert-knowledge deep dives, and recent AWS features, moved verbatim from SKILL.md.

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
