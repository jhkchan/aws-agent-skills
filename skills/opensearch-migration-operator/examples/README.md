# Example usage: opensearch-migration-operator

A walkthrough showing the skill assessing migration readiness for an
Elasticsearch 7.10 domain, demonstrating the pre-check gate, plugin
compatibility assessment, snapshot requirement, and the CONFIRM gate.

## Input (user prompt)

> We need to migrate our Elasticsearch 7.10 production search cluster
> to OpenSearch 2.x. What's the migration path and are there any blockers?

```text
Domain: prod-search-cluster
Region: us-east-1
Current version: Elasticsearch_7.10
Target version: OpenSearch_2.11
Operation: assess-migration-readiness

Cluster configuration:
  - EngineVersion: Elasticsearch_7.10
  - ClusterStatus: Active
  - ClusterHealth: green (45 indices, 12 TB)
  - Instance type: r6g.2xlarge.search
  - Node count: 6 (3 dedicated masters, 3 data)
  - Plugins: analysis-icu, analysis-phonetic, ingest-attachment
  - Snapshot repository: s3-migration-repo (registered, verified)
  - VPC: yes (VPC-only domain)
  - EncryptionAtRest: enabled
```

## Skill output

```text
OPERATION: assess
VERDICT: READY
TARGET: prod-search-cluster (ES 7.10 -> OpenSearch 2.11)
PRE_CHECKS:
  - [PASS] Domain status is Active
  - [PASS] Cluster health is green (45 indices, 12 TB)
  - [PASS] Source version Elasticsearch_7.10 is eligible for in-place upgrade
  - [PASS] All installed plugins (analysis-icu, analysis-phonetic, ingest-attachment) have OpenSearch equivalents
  - [PASS] No ES-only commercial plugins detected
  - [PASS] Snapshot repository s3-migration-repo is registered and verified
  - [PASS] No active shard relocation or recovery in progress
STEPS:
  1. Take a pre-upgrade full snapshot:
     PUT _snapshot/s3-migration-repo/pre-upgrade-snapshot?wait_for_completion=true {"indices":"*","ignore_unavailable":true,"include_global_state":true}
  2. CONFIRM: About to update-domain-config on prod-search-cluster to OpenSearch_2.11. Blue/green deployment will take 30-120 minutes. Proceed? (yes/no)
  3. aws opensearch update-domain-config --domain-name prod-search-cluster --engine-version OpenSearch_2.11 --region us-east-1
  4. Monitor: aws opensearch describe-domain --domain-name prod-search-cluster --query 'DomainStatus.{Processing:Processing,EngineVersion:EngineVersion}'
POST_VERIFY: (pending execution)
ENDPOINT: https://vpc-prod-search-cluster.us-east-1.es.amazonaws.com (unchanged — AWS blue/green preserves the endpoint)
CLIENT_NOTES:
  - OpenSearch 2.11 supports compatible=40 for ES 7.x clients.
  - Test all application search queries with compatibility mode before full cutover.
  - Plan to migrate client libraries from elasticsearch-* to opensearch-* within 3-6 months.
```

## What the skill caught that a generic assistant misses

1. **Version compatibility verification.** A generic assistant might
   recommend a direct upgrade without checking the version compatibility
   matrix. The skill verifies ES 7.10 is eligible for in-place upgrade to
   OpenSearch — the lowest-risk path because OpenSearch 1.x is a direct
   fork of ES 7.10.2.

2. **Plugin inventory.** The skill checks every installed plugin against
   the OpenSearch compatibility table. ES-only commercial plugins (X-Pack)
   would block the migration. In this case, all plugins have built-in
   OpenSearch equivalents — no blockers.

3. **Snapshot requirement.** The skill verifies the snapshot repository
   is registered AND verified. A pre-upgrade snapshot is step 1 of the
   STEPS — this is the rollback path. A generic assistant skips this.

4. **Blue/green endpoint behavior.** The skill explains that the domain
   endpoint does NOT change during AWS-managed blue/green deployment.
   Applications keep their connection strings. A generic assistant might
   suggest updating endpoints unnecessarily.

5. **Client compatibility mode.** The skill surfaces the `compatible=40`
   bridge and recommends migrating client libraries within 3-6 months.
   A generic assistant doesn't address the client library transition.

## Slash-command invocation

```
/aws:operate-opensearch-migration
```

Or via the orchestrator:

```
/aws:pipeline
You: "plan our Elasticsearch to OpenSearch migration"
```

The orchestrator emits
`[Phase: Operate | Skills routed: opensearch-migration-operator]` and
hands off to this skill for the migration block.

## Live-account follow-up (optional, requires AWS CLI)

After the upgrade completes, verify the cluster:

```bash
# Confirm domain is on OpenSearch 2.11
aws opensearch describe-domain \
  --domain-name prod-search-cluster \
  --query 'DomainStatus.{EngineVersion:EngineVersion, Processing:Processing}' \
  --output json

# Verify cluster health
ENDPOINT=$(aws opensearch describe-domain \
  --domain-name prod-search-cluster \
  --query 'DomainStatus.Endpoint' --output text)

curl -s "https://$ENDPOINT/_cluster/health?pretty"

# Verify compatible=40 mode
curl -s "https://$ENDPOINT/_cluster/health?compatible=40&pretty"

# Check plugins
curl -s "https://$ENDPOINT/_cat/plugins?v"
```

If any queries fail, test them with `?compatible=40` appended. If they
still fail, check for ES-specific API endpoints (`_xpack/*`) that
OpenSearch does not support.
