# Provisioning CLI Commands — OpenSearch Domain Deployer

Full copy-pasteable CLI command sequence for all 10 provisioning steps.
Variables to substitute: `<domain>`, `<region>`, `<account-id>`, KMS
key ARNs, subnet IDs, security group IDs, IAM role ARNs, instance
type, instance count.

## Step 0: Prerequisites check

```bash
# Confirm caller identity
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"

# Confirm region
REGION=$(aws configure get region)
echo "Region: $REGION"

# Confirm domain name is available
aws opensearch describe-domain --domain-name <domain> 2>&1 | head -3

# Confirm CMK exists and is enabled (if encryption at rest with customer CMK)
aws kms describe-key --key-id alias/<alias-name> \
  --query 'KeyMetadata.[KeyId,KeyState,Enabled]' --output text

# Confirm VPC subnets span 3 AZs (for Multi-AZ + VPC access)
aws ec2 describe-subnets --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc \
  --query 'Subnets[*].AvailabilityZone' --output text
# Expect 3 distinct AZ values

# Confirm master IAM role exists (if FGAC with IAM)
aws iam get-role --role-name <master-role>

# Confirm snapshot IAM role exists
aws iam get-role --role-name <snapshot-role>

# Confirm snapshot S3 bucket exists
aws s3api head-bucket --bucket <snapshot-bucket>
```

## Step 1: Create the security group (VPC-only access)

```bash
aws ec2 create-security-group \
  --group-name opensearch-prod-sg \
  --description "Security group for prod OpenSearch domain" \
  --vpc-id vpc-0aaa

# Inbound: allow the application's SG to reach port 443 (HTTPS)
aws ec2 authorize-security-group-ingress \
  --group-id sg-search123 \
  --protocol tcp \
  --port 443 \
  --source-security-group-id sg-app456
```

## Step 2: Create IAM roles (master user + snapshot)

### Master user role (for FGAC with IAM)

```bash
aws iam create-role \
  --role-name opensearch-master \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::<account-id>:root"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach a minimal policy — master users get full access via FGAC,
# but the IAM role itself needs to be assumable.
aws iam put-role-policy \
  --role-name opensearch-master \
  --policy-name opensearch-master-policy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": "es:*",
      "Resource": "arn:aws:es:<region>:<account-id>:domain/<domain>/*"
    }]
  }'
```

### Snapshot role (for manual snapshots to S3)

```bash
aws iam create-role \
  --role-name opensearch-snapshot \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "es.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam put-role-policy \
  --role-name opensearch-snapshot \
  --policy-name opensearch-snapshot-policy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {"Effect": "Allow", "Action": ["s3:ListBucket"], "Resource": ["arn:aws:s3:::<snapshot-bucket>"]},
      {"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"], "Resource": ["arn:aws:s3:::<snapshot-bucket>/*"]}
    ]
  }'
```

## Step 3: Create the S3 bucket for manual snapshots

```bash
aws s3api create-bucket \
  --bucket <snapshot-bucket> \
  --region <region> \
  --create-bucket-configuration LocationConstraint=<region>

# Enable default encryption on the bucket
aws s3api put-bucket-encryption \
  --bucket <snapshot-bucket> \
  --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
```

## Step 4: Create the customer CMK (for encryption at rest)

```bash
aws kms create-key --description "Customer CMK for OpenSearch <domain>"

aws kms create-alias \
  --alias-name alias/<alias-name> \
  --target-key-id <key-id>
```

## Step 5: Create the OpenSearch domain (managed cluster, Multi-AZ)

The canonical production pattern: 6 data nodes Multi-AZ + 3 dedicated
masters, EBS gp3, customer CMK, VPC-only, FGAC with IAM master user.

```bash
aws opensearch create-domain \
  --domain-name <domain> \
  --engine-version OpenSearch_2.11 \
  --cluster-config \
    InstanceType=r6g.2xlarge.search,InstanceCount=6,\
DedicatedMasterEnabled=true,DedicatedMasterType=c6g.large.search,DedicatedMasterCount=3,\
ZoneAwarenessEnabled=true,ZoneAwarenessConfig={AvailabilityZoneCount=3} \
  --ebs-options EBSEnabled=true,VolumeType=gp3,VolumeSize=100 \
  --encryption-at-rest-options \
    Enabled=true,KmsKeyId=arn:aws:kms:<region>:<account-id>:alias/<alias-name> \
  --node-to-node-encryption-options Enabled=true \
  --domain-endpoint-options EnforceHTTPS=true,TLSSecurityPolicy=Policy-Min-TLS-1-2-2019-07 \
  --advanced-security-options \
    Enabled=true,InternalUserDatabaseEnabled=false,\
MasterUserOptions={MasterUserARN=arn:aws:iam::<account-id>:role/opensearch-master} \
  --vpc-options \
    SubnetIds=subnet-0aaa,subnet-0bbb,subnet-0ccc,SecurityGroupIds=sg-search123 \
  --log-publishing-options \
    LogType=INDEX_SLOW_LOGS,\
CloudWatchLogsLogGroupArn=arn:aws:logs:<region>:<account-id>:log-group:<domain>-index-slow,Enabled=true \
  --log-publishing-options \
    LogType=SEARCH_SLOW_LOGS,\
CloudWatchLogsLogGroupArn=arn:aws:logs:<region>:<account-id>:log-group:<domain>-search-slow,Enabled=true \
  --snapshot-options AutomatedSnapshotStartHour=3 \
  --access-policies file://access-policy.json \
  --tags Key=Environment,Value=production Key=Workload,Value=search
```

Sample `access-policy.json` (resource-based policy for IAM FGAC):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": "*"},
      "Action": "es:*",
      "Resource": "arn:aws:es:<region>:<account-id>:domain/<domain>/*"
    }
  ]
}
```

Note: with FGAC enabled, the resource-based policy should be open
(`"Principal": {"AWS": "*"}`) — FGAC handles authentication at the
OpenSearch layer, not the resource-policy layer.

Wait for the domain to become active (10-30 minutes):

```bash
aws opensearch describe-domain --domain-name <domain> \
  --query 'DomainStatus.[Processing,Endpoint,Created]'
# Wait for Processing=false, Created=true
```

## Step 5 alt A: Managed cluster, no Multi-AZ (dev / test)

```bash
aws opensearch create-domain \
  --domain-name <domain> \
  --engine-version OpenSearch_2.11 \
  --cluster-config \
    InstanceType=t3.small.search,InstanceCount=1,\
DedicatedMasterEnabled=false,ZoneAwarenessEnabled=false \
  --ebs-options EBSEnabled=true,VolumeType=gp3,VolumeSize=10 \
  --encryption-at-rest-options Enabled=true \
  --node-to-node-encryption-options Enabled=true \
  --domain-endpoint-options EnforceHTTPS=true,TLSSecurityPolicy=Policy-Min-TLS-1-2-2019-07 \
  --access-policies file://access-policy.json \
  --tags Key=Environment,Value=dev
```

## Step 5 alt B: Managed cluster with UltraWarm

```bash
aws opensearch create-domain \
  --domain-name <domain> \
  --engine-version OpenSearch_2.11 \
  --cluster-config \
    InstanceType=r6g.2xlarge.search,InstanceCount=6,\
DedicatedMasterEnabled=true,DedicatedMasterType=c6g.large.search,DedicatedMasterCount=3,\
ZoneAwarenessEnabled=true,ZoneAwarenessConfig={AvailabilityZoneCount=3},\
WarmEnabled=true,WarmType=ultrawarm1.medium.search,WarmCount=3 \
  --ebs-options EBSEnabled=true,VolumeType=gp3,VolumeSize=100 \
  --encryption-at-rest-options Enabled=true \
  --node-to-node-encryption-options Enabled=true \
  --domain-endpoint-options EnforceHTTPS=true,TLSSecurityPolicy=Policy-Min-TLS-1-2-2019-07 \
  --advanced-security-options \
    Enabled=true,InternalUserDatabaseEnabled=false,\
MasterUserOptions={MasterUserARN=arn:aws:iam::<account-id>:role/opensearch-master} \
  --vpc-options SubnetIds=subnet-0aaa,subnet-0bbb,subnet-0ccc,SecurityGroupIds=sg-search123 \
  --tags Key=Environment,Value=production
```

## Step 6: OpenSearch Serverless (separate API)

```bash
# Create the encryption security policy (required before collection creation)
aws opensearchserverless create-security-policy \
  --name prod-serverless-encryption \
  --type encryption \
  --policy file://encryption-policy.json

# Sample encryption-policy.json:
# {
#   "Rules": [{"ResourceType": "collection", "Resource": ["collection/prod-serverless"]}],
#   "KMSARN": "arn:aws:kms:<region>:<account-id>:alias/<alias-name>"
# }

# Create the network security policy
aws opensearchserverless create-security-policy \
  --name prod-serverless-network \
  --type network \
  --policy file://network-policy.json

# Sample network-policy.json:
# {
#   "Rules": [{"ResourceType": "collection", "Resource": ["collection/prod-serverless"]}],
#   "AllowFromPublic": false,
#   "SourceVPCEs": ["vpce-0aaa"]
# }

# Create the collection
aws opensearchserverless create-collection \
  --name prod-serverless \
  --type SEARCH \
  --description "Serverless search collection"

# Wait for the collection to become active
aws opensearchserverless batch-get-collection --names prod-serverless
```

## Step 7: Vector search collection (Serverless)

```bash
aws opensearchserverless create-collection \
  --name prod-vectors \
  --type VECTORSEARCH \
  --description "Vector search collection for k-NN"

# Create the vector index via the OpenSearch API
# (use the collection endpoint after it becomes active)
curl -X PUT "https://<collection-endpoint>/products" \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {
      "index": {
        "knn": true,
        "number_of_shards": 1,
        "number_of_replicas": 1
      }
    },
    "mappings": {
      "properties": {
        "product-vector": {
          "type": "knn_vector",
          "dimension": 1536,
          "method": {
            "name": "hnsw",
            "space_type": "l2",
            "engine": "nmslib",
            "parameters": {"ef_construction": 128, "m": 24}
          }
        }
      }
    }
  }'
```

## Step 8: Register the manual snapshot repository

After the domain is active, register the snapshot repository via the
OpenSearch API. Use IAM SigV4 signing (with the master IAM role
credentials) to authenticate.

```bash
# Use curl with AWS SigV4 signing (via --aws-sigv4 with curl 7.75+)
curl -X PUT "https://<endpoint>/_snapshot/manual-snapshots" \
  --aws-sigv4 "aws:amz:<region>:es" \
  --user "master-user:master-password" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "s3",
    "settings": {
      "bucket": "<snapshot-bucket>",
      "region": "<region>",
      "role_arn": "arn:aws:iam::<account-id>:role/opensearch-snapshot"
    }
  }'

# Take a manual snapshot
curl -X PUT "https://<endpoint>/_snapshot/manual-snapshots/$(date +%Y-%m-%d-%H-%M)" \
  --aws-sigv4 "aws:amz:<region>:es" \
  --user "master-user:master-password"

# Restore from snapshot (creates a new index — use a rename pattern to avoid clobbering)
curl -X POST "https://<endpoint>/_snapshot/manual-snapshots/<snapshot>/_restore" \
  --aws-sigv4 "aws:amz:<region>:es" \
  --user "master-user:master-password" \
  -H "Content-Type: application/json" \
  -d '{
    "indices": "logs-*",
    "rename_pattern": "logs-(.+)",
    "rename_replacement": "restored-logs-$1"
  }'
```

## Step 9: Create index templates and ISM policies

### Index template (default settings for new indices)

```bash
curl -X PUT "https://<endpoint>/_index_template/logs-template" \
  --aws-sigv4 "aws:amz:<region>:es" \
  --user "master-user:master-password" \
  -H "Content-Type: application/json" \
  -d '{
    "index_patterns": ["logs-*"],
    "template": {
      "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1,
        "index.refresh_interval": "1s"
      }
    }
  }'
```

### ISM policy (hot → warm → cold → delete)

```bash
curl -X PUT "https://<endpoint>/_plugins/_ism/policies/logs-lifecycle" \
  --aws-sigv4 "aws:amz:<region>:es" \
  --user "master-user:master-password" \
  -H "Content-Type: application/json" \
  -d '{
    "policy": {
      "default_state": "hot",
      "states": [
        {"name": "hot", "actions": [], "transitions": [{"state_name": "warm", "conditions": {"min_index_age": "7d"}}]},
        {"name": "warm", "actions": [], "transitions": [{"state_name": "cold", "conditions": {"min_index_age": "30d"}}]},
        {"name": "cold", "actions": [], "transitions": [{"state_name": "delete", "conditions": {"min_index_age": "365d"}}]},
        {"name": "delete", "actions": [{"delete": {}}]}
      ]
    }
  }'
```

## Step 10: CloudWatch alarms

```bash
# Cluster status red (urgent — primary shards unavailable)
aws cloudwatch put-metric-alarm \
  --alarm-name "<domain>-cluster-status-red" \
  --namespace AWS/ES \
  --metric-name ClusterStatus.red \
  --dimensions Name=DomainName,Value=<domain> Name=ClientId,Value=<account-id> \
  --statistic Maximum --period 60 --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold --evaluation-periods 1 \
  --alarm-actions <sns-arn>

# Cluster status yellow (warning — replica shards unavailable)
aws cloudwatch put-metric-alarm \
  --alarm-name "<domain>-cluster-status-yellow" \
  --namespace AWS/ES \
  --metric-name ClusterStatus.yellow \
  --dimensions Name=DomainName,Value=<domain> Name=ClientId,Value=<account-id> \
  --statistic Maximum --period 60 --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold --evaluation-periods 5 \
  --alarm-actions <sns-arn>

# CPU > 80% for 5 min
aws cloudwatch put-metric-alarm \
  --alarm-name "<domain>-cpu-high" \
  --namespace AWS/ES \
  --metric-name CPUUtilization \
  --dimensions Name=DomainName,Value=<domain> Name=ClientId,Value=<account-id> \
  --statistic Average --period 60 --threshold 80 \
  --comparison-operator GreaterThan --evaluation-periods 5 \
  --alarm-actions <sns-arn>

# JVM memory > 85% (heap pressure)
aws cloudwatch put-metric-alarm \
  --alarm-name "<domain>-jvm-memory-high" \
  --namespace AWS/ES \
  --metric-name JVMMemoryPressure \
  --dimensions Name=DomainName,Value=<domain> Name=ClientId,Value=<account-id> \
  --statistic Average --period 60 --threshold 85 \
  --comparison-operator GreaterThan --evaluation-periods 3 \
  --alarm-actions <sns-arn>

# Disk use > 80% (approaching write-block watermark)
aws cloudwatch put-metric-alarm \
  --alarm-name "<domain>-disk-high" \
  --namespace AWS/ES \
  --metric-name FreeStorageSpace \
  --dimensions Name=DomainName,Value=<domain> Name=ClientId,Value=<account-id> \
  --statistic Average --period 300 --threshold 20000 \
  --comparison-operator LessThan --evaluation-periods 1 \
  --alarm-actions <sns-arn>
```

## Step 11: Modify an existing domain (mutable settings)

```bash
# Scale up instance count (must be multiple of 3 for Multi-AZ)
aws opensearch update-domain-config \
  --domain-name <domain> \
  --cluster-config InstanceType=r6g.2xlarge.search,InstanceCount=9

# Scale up EBS size
aws opensearch update-domain-config \
  --domain-name <domain> \
  --ebs-options EBSEnabled=true,VolumeType=gp3,VolumeSize=200

# Change dedicated master type
aws opensearch update-domain-config \
  --domain-name <domain> \
  --cluster-config DedicatedMasterType=c6g.2xlarge.search

# Enable UltraWarm post-creation
aws opensearch update-domain-config \
  --domain-name <domain> \
  --cluster-config WarmEnabled=true,WarmType=ultrawarm1.medium.search,WarmCount=3
```

Note: the following CANNOT be modified post-creation:
- Encryption at rest (off → on requires new domain + reindex)
- FGAC mode (IAM ↔ Cognito requires new domain + reindex)
- VPC ↔ public access (requires new domain)

## Verification

```bash
# Domain config — InstanceType, InstanceCount, MultiAZ, DedicatedMaster,
# EBS, EncryptionAtRest, NodeToNodeEncryption, AdvancedSecurityOptions,
# VPCOptions, SnapshotOptions
aws opensearch describe-domain --domain-name <domain>
aws opensearch describe-domain-config --domain-name <domain>

# Security group
aws ec2 describe-security-groups --group-ids sg-search123

# KMS key
aws kms describe-key --key-id alias/<alias-name>

# Master IAM role
aws iam get-role --role-name opensearch-master

# Snapshot IAM role
aws iam get-role --role-name opensearch-snapshot

# S3 bucket
aws s3api head-bucket --bucket <snapshot-bucket>

# Serverless collections (if applicable)
aws opensearchserverless batch-get-collection --names <collection>

# CloudWatch alarms
aws cloudwatch describe-alarms --alarm-name-prefix "<domain>-"
```

## Terraform equivalent (aws_opensearch_domain)

```hcl
resource "aws_opensearch_domain" "search" {
  domain_name    = "<domain>"
  engine_version = "OpenSearch_2.11"

  cluster_config {
    instance_type           = "r6g.2xlarge.search"
    instance_count          = 6
    dedicated_master_enabled = true
    dedicated_master_type   = "c6g.large.search"
    dedicated_master_count  = 3
    zone_awareness_enabled  = true

    zone_awareness_config {
      availability_zone_count = 3
    }
  }

  ebs_options {
    ebs_enabled = true
    volume_size = 100
    volume_type = "gp3"
  }

  encrypt_at_rest {
    enabled    = true
    kms_key_id = aws_kms_key.opensearch.arn
  }

  node_to_node_encryption {
    enabled = true
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  advanced_security_options {
    enabled                        = true
    internal_user_database_enabled = false
    master_user_options {
      master_user_arn = aws_iam_role.opensearch_master.arn
    }
  }

  vpc_options {
    subnet_ids         = [aws_subnet.search_a.id, aws_subnet.search_b.id, aws_subnet.search_c.id]
    security_group_ids = [aws_security_group.search.id]
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.index_slow.arn
    log_type                 = "INDEX_SLOW_LOGS"
    enabled                  = true
  }

  snapshot_options {
    automated_snapshot_start_hour = 3
  }

  tags = {
    Environment = "production"
    Workload    = "search"
  }
}

resource "aws_kms_key" "opensearch" {
  description             = "Customer CMK for OpenSearch <domain>"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}

resource "aws_kms_alias" "opensearch" {
  name          = "alias/<alias-name>"
  target_key_id = aws_kms_key.opensearch.key_id
}

resource "aws_security_group" "search" {
  name        = "opensearch-prod-sg"
  description = "Security group for prod OpenSearch domain"
  vpc_id      = var.vpc_id

  ingress {
    from_port                = 443
    to_port                  = 443
    protocol                 = "tcp"
    security_groups          = [var.app_security_group_id]
  }
}
```

## AWS CLI quick reference

| Operation | Command |
|---|---|
| Create managed domain | `aws opensearch create-domain` |
| Update domain config | `aws opensearch update-domain-config` |
| Describe domain | `aws opensearch describe-domain` |
| Describe domain config | `aws opensearch describe-domain-config` |
| Delete domain | `aws opensearch delete-domain` |
| List domain names | `aws opensearch list-domain-names` |
| Create Serverless collection | `aws opensearchserverless create-collection` |
| Get Serverless collection | `aws opensearchserverless batch-get-collection` |
| Create Serverless security policy | `aws opensearchserverless create-security-policy` |
| Create Serverless access policy | `aws opensearchserverless create-access-policy` |
| Create Serverless VPC endpoint | `aws opensearchserverless create-vpc-endpoint` |
| List tags | `aws opensearch list-tags --arn <domain-arn>` |
