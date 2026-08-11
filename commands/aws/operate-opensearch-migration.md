---
description: Manage Elasticsearch to OpenSearch migration operations — version compatibility assessment (ES 5.x/6.x/7.x to OpenSearch 1.x/2.x), index migration via snapshot/restore to S3 and reindex-from-remote, plugin compatibility, client compatibility mode (compatible=40), in-place upgrade vs new cluster migration, snapshot repository setup, blue/green downtime planning, and OpenSearch 2.x features (neural search, vector DB, flow frameworks).
nl_triggers:
  - "migrate Elasticsearch to OpenSearch"
  - "ES to OpenSearch migration"
  - "OpenSearch version compatibility"
  - "OpenSearch snapshot repository S3"
  - "reindex from remote OpenSearch"
  - "OpenSearch plugin compatibility"
  - "OpenSearch client compatibility mode"
  - "in-place upgrade OpenSearch"
  - "blue/green migration OpenSearch"
  - "OpenSearch 2.x migration"
  - "OpenSearch neural search"
  - "OpenSearch vector DB"
  - "OpenSearch flow frameworks"
  - "post-migration verification OpenSearch"
  - "Elasticsearch deprecation migration"
routes_to: opensearch-migration-operator
---

# /aws:operate-opensearch-migration

Activate the `opensearch-migration-operator` skill and plan/execute an
Elasticsearch to OpenSearch migration with deterministic pre-checks,
CONFIRM gate, and post-verification.

## What it does

Reads a domain configuration plus the intended migration operation and
applies the priority-ordered pre-check sequence:

1. Pre-flight domain metadata gate — short-circuit `Processing`/
   `Upgrading` states, version detection, cluster health.
2. Version compatibility assessment — ES 5.x/6.x/7.x to OpenSearch 1.x/
   2.x compatibility matrix check.
3. Plugin compatibility gate — BLOCKED if ES-only commercial plugins are
   installed (X-Pack security, ML, SQL, alerting).
4. Snapshot repository verification — S3 bucket, IAM role, repository
   registration and `_verify` check.
5. READY — emit the exact CLI/API sequence, endpoint behavior, client
   compatibility notes, and the CONFIRM gate prompt.
6. Execute behind CONFIRM gate — snapshot, upgrade or reindex, wait for
   completion.
7. Post-verification — cluster health, document counts, mappings, query
   compatibility, plugin confirmation. COMPLETED only if ALL checks pass.

Emits a deterministic VERDICT per operation:

```text
OPERATION: <assess | snapshot-setup | in-place-upgrade | new-cluster-reindex | blue-green | verify>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <domain-name, source-version, target-version>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI or API command>
POST_VERIFY:
  - [PASS] <verification description>
ENDPOINT: <endpoint behavior>
CLIENT_NOTES: <compatibility mode, client library notes>
```

## When to invoke

Paste a domain configuration plus the intended operation, or just
describe the scenario and ask any of:

- "migrate our Elasticsearch cluster to OpenSearch"
- "can we upgrade ES 7.10 in-place to OpenSearch?"
- "set up a snapshot repository for migration"
- "reindex from remote to our new OpenSearch cluster"
- "are our plugins compatible with OpenSearch?"
- "verify our OpenSearch migration completed"
- "does compatible=40 work for our clients?"

A bare domain name + any migration verb also routes here via the
orchestrator.

## Inputs

- Domain configuration (`describe-domain` JSON): engine version, cluster
  config, status, plugins, snapshot repositories, VPC settings.
- Source and target versions for compatibility assessment.
- Plugin inventory (`_cat/plugins` output).
- S3 snapshot repository details (bucket, IAM role, registration status).
- For reindex-from-remote: source endpoint, target endpoint, network
  connectivity confirmation.

## Outputs

- One VERDICT block per operation.
- PRE_CHECKS list with `[PASS]` / `[FAIL]` per check.
- For READY: the exact CLI/API sequence, endpoint behavior, client
  compatibility notes, and the CONFIRM gate prompt.
- For COMPLETED: POST_VERIFY list, endpoint info, client notes.
- For BLOCKED: specific failure reason and remediation guidance.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 4 Operate specialist for ES-to-OpenSearch migration).
- `/aws:audit-opensearch-domain` for the security/compliance posture of
  the OpenSearch domain before or after migration.
- `/aws:deploy-opensearch-domain` for provisioning a new OpenSearch
  domain as a migration target.
