# Migration Procedures

Detailed CLI and API scripts for Elasticsearch to OpenSearch migration
operations referenced by the opensearch-migration-operator skill.

## Pre-flight data gathering

### Domain metadata and version check

```bash
#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${1:?Usage: $0 <domain-name>}"
REGION="${2:-us-east-1}"

echo "=== Domain metadata (OpenSearch) ==="
aws opensearch describe-domain \
  --domain-name "$DOMAIN" \
  --region "$REGION" \
  --query 'DomainStatus.{
    EngineVersion:EngineVersion,
    Processing:Processing,
    ClusterConfig:ClusterConfig,
    EBSOptions:EBSOptions,
    EncryptionAtRestOptions:EncryptionAtRestOptions,
    VPCOptions:VPCOptions,
    Endpoint:Endpoint,
    Snapshots:SnapshotOptions
  }' \
  --output json 2>/dev/null || echo "Not an OpenSearch domain"

echo ""
echo "=== Domain metadata (legacy Elasticsearch) ==="
aws es describe-elasticsearch-domain \
  --domain-name "$DOMAIN" \
  --region "$REGION" \
  --query 'DomainStatus.{
    ElasticsearchVersion:ElasticsearchVersion,
    ElasticsearchClusterConfig:ElasticsearchClusterConfig,
    EBSOptions:EBSOptions,
    EncryptionAtRestOptions:EncryptionAtRestOptions,
    VPCOptions:VPCOptions,
    Endpoint:Endpoint,
    Snapshots:SnapshotOptions
  }' \
  --output json 2>/dev/null || echo "Not an Elasticsearch domain"
```

### Cluster health and inventory (via curl)

```bash
ENDPOINT="${1:?Usage: $0 <endpoint-url>}"

echo "=== Cluster health ==="
curl -s "https://$ENDPOINT/_cluster/health?pretty"

echo ""
echo "=== Plugin inventory ==="
curl -s "https://$ENDPOINT/_cat/plugins?v"

echo ""
echo "=== Node info (detailed plugins) ==="
curl -s "https://$ENDPOINT/_nodes/plugins" | python3 -m json.tool

echo ""
echo "=== Index inventory ==="
curl -s "https://$ENDPOINT/_cat/indices?v&h=index,docs.count,store.size,health,status"

echo ""
echo "=== Snapshot repositories ==="
curl -s "https://$ENDPOINT/_snapshot?pretty"

echo ""
echo "=== Index mappings (for compatibility check) ==="
curl -s "https://$ENDPOINT/_mapping?pretty" | head -200
```

## S3 snapshot repository setup

### Create the IAM role for snapshot access

```bash
cat > /tmp/os-snapshot-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "es.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

aws iam create-role \
  --role-name OpenSearchSnapshotRole \
  --assume-role-policy-document file:///tmp/os-snapshot-trust-policy.json

cat > /tmp/os-snapshot-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::migration-snapshots-bucket"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::migration-snapshots-bucket/*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name OpenSearchSnapshotRole \
  --policy-name OpenSearchSnapshotPolicy \
  --policy-document file:///tmp/os-snapshot-policy.json
```

### Register the repository via the OpenSearch API

```bash
ENDPOINT="${1:?Usage: $0 <endpoint-url>}"
BUCKET="${2:-migration-snapshots-bucket}"
ROLE_ARN="${3:?Usage: $0 <endpoint> <bucket> <role-arn>}"

# Register the repository
curl -s -X PUT "https://$ENDPOINT/_snapshot/s3-migration-repo" \
  -H "Content-Type: application/json" \
  -d "{
    \"type\": \"s3\",
    \"settings\": {
      \"bucket\": \"$BUCKET\",
      \"region\": \"us-east-1\",
      \"base_path\": \"opensearch-migration\",
      \"role_arn\": \"$ROLE_ARN\"
    }
  }"

echo ""
echo "=== Verify repository ==="
curl -s -X POST "https://$ENDPOINT/_snapshot/s3-migration-repo/_verify?pretty"
```

## Full snapshot and restore

### Take a snapshot on the source cluster

```bash
ENDPOINT="${1:?Usage: $0 <source-endpoint>}"

curl -s -X PUT "https://$ENDPOINT/_snapshot/s3-migration-repo/migration-snapshot?wait_for_completion=true" \
  -H "Content-Type: application/json" \
  -d '{
    "indices": "*",
    "ignore_unavailable": true,
    "include_global_state": false
  }'

echo ""
echo "=== Snapshot status ==="
curl -s "https://$ENDPOINT/_snapshot/s3-migration-repo/migration-snapshot?pretty"
```

### Restore on the target cluster

```bash
TARGET_ENDPOINT="${1:?Usage: $0 <target-endpoint>}"

# Register the same repository on the target first (same S3 bucket)

# Restore
curl -s -X POST "https://$TARGET_ENDPOINT/_snapshot/s3-migration-repo/migration-snapshot/_restore?wait_for_completion=false" \
  -H "Content-Type: application/json" \
  -d '{
    "indices": "*",
    "ignore_unavailable": true,
    "include_global_state": false
  }'

echo ""
echo "=== Recovery status ==="
curl -s "https://$TARGET_ENDPOINT/_cat/recovery?v"
```

## Reindex from remote

### Enable remote reindex on the target domain

For AWS-managed OpenSearch, configure the domain to allow reindex from
remote:

```bash
aws opensearch update-domain-config \
  --domain-name target-opensearch-cluster \
  --advanced-security-options '{
    "Enabled": true
  }' \
  --domain-endpoint-options '{
    "EnforceHTTPS": true
  }' \
  --region us-east-1

# The reindex.remote.whitelist setting must be configured in the
# domain's advanced configuration. For AWS-managed domains, this is
# set via the console or CLI:
aws opensearch update-domain-config \
  --domain-name target-opensearch-cluster \
  --log-publishing-options '{
    "IndexSlowLogs": {"Enabled": true, "CloudWatchLogsLogGroupArn": "arn:aws:logs:us-east-1:111111111111:log-group:/aws/opensearch/index-slow-logs"}
  }'
```

### Execute reindex from remote

```bash
SOURCE_ENDPOINT="${1:?Usage: $0 <source-endpoint>}"
TARGET_ENDPOINT="${2:?Usage: $0 <target-endpoint>}"
INDEX="${3:?Usage: $0 <source> <target> <index-name>}"

# Create the target index with correct mappings first
curl -s -X PUT "https://$TARGET_ENDPOINT/$INDEX" \
  -H "Content-Type: application/json" \
  -d @mappings/$INDEX.json

# Reindex from remote
curl -s -X POST "https://$TARGET_ENDPOINT/_reindex?wait_for_completion=false" \
  -H "Content-Type: application/json" \
  -d "{
    \"source\": {
      \"remote\": {
        \"host\": \"https://$SOURCE_ENDPOINT:443\",
        \"username\": \"reindex-user\",
        \"password\": \"reindex-password\"
      },
      \"index\": \"$INDEX\",
      \"size\": 5000
    },
    \"dest\": {
      \"index\": \"$INDEX\"
    }
  }"

# Check task status
TASK_ID="<task-id-from-previous-response>"
curl -s "https://$TARGET_ENDPOINT/_tasks/$TASK_ID?pretty"
```

## In-place upgrade (AWS-managed)

```bash
DOMAIN="${1:?Usage: $0 <domain-name>}"
TARGET_VERSION="${2:?Usage: $0 <domain> <target-version> e.g. OpenSearch_2.11}"

# Take a pre-upgrade snapshot
ENDPOINT=$(aws opensearch describe-domain \
  --domain-name "$DOMAIN" \
  --query 'DomainStatus.Endpoint' \
  --output text)

curl -s -X PUT "https://$ENDPOINT/_snapshot/s3-migration-repo/pre-upgrade-$(date +%s)?wait_for_completion=true" \
  -H "Content-Type: application/json" \
  -d '{"indices":"*","ignore_unavailable":true,"include_global_state":true}'

# Trigger the upgrade
aws opensearch update-domain-config \
  --domain-name "$DOMAIN" \
  --engine-version "$TARGET_VERSION" \
  --region us-east-1

# Monitor upgrade progress
aws opensearch describe-domain \
  --domain-name "$DOMAIN" \
  --query 'DomainStatus.{Processing:Processing, UpgradeProcessing:UpgradeProcessing, EngineVersion:EngineVersion}' \
  --output json
```

## Post-migration verification

```bash
TARGET_ENDPOINT="${1:?Usage: $0 <target-endpoint>}"

echo "=== Cluster health ==="
curl -s "https://$TARGET_ENDPOINT/_cluster/health?pretty"

echo ""
echo "=== Plugin verification ==="
curl -s "https://$TARGET_ENDPOINT/_cat/plugins?v"

echo ""
echo "=== Index document counts ==="
curl -s "https://$TARGET_ENDPOINT/_cat/indices?v&h=index,docs.count,store.size,health"

echo ""
echo "=== Compatibility mode test ==="
curl -s "https://$TARGET_ENDPOINT/_cluster/health?compatible=40&pretty"

echo ""
echo "=== Snapshot repository on target ==="
curl -s "https://$TARGET_ENDPOINT/_snapshot?pretty"

echo ""
echo "=== Test search (with compatibility mode) ==="
curl -s "https://$TARGET_ENDPOINT/_search?compatible=40&size=0&pretty" \
  -H "Content-Type: application/json" \
  -d '{"query":{"match_all":{}}}'
```

## Document count comparison

Compare document counts between source and target to verify migration
completeness.

```bash
SOURCE_ENDPOINT="${1:?Usage: $0 <source> <target>}"
TARGET_ENDPOINT="${2:?Usage: $0 <source> <target>}"

INDICES=$(curl -s "https://$SOURCE_ENDPOINT/_cat/indices?h=index" | sort)

echo "index,source_count,target_count,match"
for IDX in $INDICES; do
  SRC_COUNT=$(curl -s "https://$SOURCE_ENDPOINT/_cat/indices/$IDX?h=docs.count" | tr -d '[:space:]')
  TGT_COUNT=$(curl -s "https://$TARGET_ENDPOINT/_cat/indices/$IDX?h=docs.count" | tr -d '[:space:]')
  if [ "$SRC_COUNT" = "$TGT_COUNT" ]; then
    echo "$IDX,$SRC_COUNT,$TGT_COUNT,YES"
  else
    echo "$IDX,$SRC_COUNT,$TGT_COUNT,NO"
  fi
done
```
