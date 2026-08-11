# Directory Bucket Configuration Patterns Reference

Supplementary reference for the S3 Directory Bucket Deployer skill.
Covers the name format parser, zone-affinity compute patterns, table
bucket vs directory bucket decision matrix, and the limitations matrix.

## Directory bucket name format parser

```text
  my-app-data--use1-az1--x-s3
  |          |  |        |  |
  |----------|  |--------|  |
   base name    AZ ID      mandatory suffix
```

| Segment | Format | Example | Validation |
|---|---|---|---|
| Base name | lowercase, alphanumeric, single hyphens | `my-app-data` | NO `--` inside; DNS-compatible |
| Delimiter | double-dash `--` | `--` | exactly two hyphens |
| AZ ID | `xxxx-azN` | `use1-az1` | resolved from AZ name via EC2 API |
| Delimiter | double-dash `--` | `--` | exactly two hyphens |
| Suffix | `x-s3` | `x-s3` | mandatory, case-sensitive |

Common parsing failures:
- `my-app--data--use1-az1--x-s3` — base name contains `--` (rejected)
- `my-app-data-use1-az1-x-s3` — single-dash delimiter (rejected)
- `my-app-data--use1-az1--X-S3` — uppercase suffix (rejected)
- `my-app-data--us-east-1a--x-s3` — AZ name instead of AZ ID (rejected)

## Zone-affinity compute patterns

### EC2 direct placement

```bash
# Pin EC2 to the directory bucket's AZ via subnet
aws ec2 run-instances \
  --image-id ami-<AMI> \
  --instance-type c7n.large \
  --subnet-id subnet-<SUBNET_IN_TARGET_AZ>
```

### EC2 Auto Scaling Group (single AZ)

```bash
# Restrict ASG to subnets in the target AZ only
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name zone-affinity-asg \
  --launch-template LaunchTemplateName=app-template \
  --min-size 2 --max-size 8 \
  --vpc-zone-identifier "subnet-aaa,subnet-aaa"
  # Both subnet IDs must be in the same AZ (use1-az1)
```

### ECS task placement constraint

```bash
# Pin ECS tasks to the target AZ
aws ecs register-task-definition \
  --family zone-affinity-task \
  --placement-constraints type=memberOf,expression="attribute:ecs.availability-zone == use1-az1"
```

### EKS node group

```bash
# Node group with subnets only in the target AZ
eksctl create nodegroup \
  --cluster zone-affinity-cluster \
  --name zone-affinity-nodes \
  --node-type c7n.large \
  --nodes 4 --nodes-min 2 --nodes-max 8 \
  --region us-east-1
# The nodegroup inherits AZ from the subnet IDs passed via --subnets
```

### Capacity Reservation guarantee

```bash
aws ec2 create-capacity-reservation \
  --instance-type c7n.large \
  --availability-zone-id use1-az1 \
  --instance-platform Linux/UNIX \
  --instance-count 4
```

## Table bucket vs directory bucket decision matrix

| Workload type | Use directory bucket | Use table bucket |
|---|---|---|
| High-throughput object reads/writes | Yes | No |
| Analytics on tabular data (Iceberg) | No | Yes |
| ML training data pipeline | Yes (for objects) | Yes (for structured features) |
| Application cache / scratch pad | Yes | No |
| Data lake query (Athena/Spark) | No (use table bucket) | Yes |
| Key-value store pattern | Yes | No |
| Time-series append-only | Possible | Yes (Iceberg native) |

Table buckets are created via `aws s3tables create-table-bucket` and
support table-level operations only. Directory buckets are created via
`aws s3api create-directory-bucket` and support object-level operations.

## S3 Express One Zone limitations matrix

| Feature | Standard S3 (General Purpose) | S3 Express One Zone (Directory) |
|---|---|---|
| Availability | Multi-AZ (>=3) | Single AZ |
| Cross-region replication | Supported | **NOT supported** |
| Same-region replication | Supported | **NOT supported** |
| Versioning | Supported | **NOT supported** |
| Object Lock | Supported | **NOT supported** |
| Transfer Acceleration | Supported | **NOT supported** |
| Lifecycle policies | Supported | Limited support |
| Bucket policies | `arn:aws:s3:::` ARN | `arn:aws:s3express:` ARN |
| Endpoint | Regional | Zonal |
| Latency | 10-100ms | Single-digit ms (same AZ) |
| Requests/sec | High | Highest |
| Durability | 99.999999999% (11 nines) | 99.9999999% (9 nines, single AZ) |

**Key compliance implication:** the single-AZ durability (9 nines) and
no-CRR/no-versioning limitations mean directory buckets are unsuitable
for compliance archives, long-term backups, or data that requires
cross-AZ or cross-region durability guarantees.

## S3 Express One Zone pricing characteristics

- **Storage:** priced per GB-month, typically comparable to or slightly
  higher than S3 Standard
- **PUT/POST/LIST requests:** priced per 1,000 requests
- **GET/SELECT requests:** priced per 1,000 requests (lower than Standard)
- **Data retrieval:** priced per GB
- **Same-AZ data transfer:** FREE (directory bucket to compute in same AZ)
- **Cross-AZ data transfer:** $0.01/GB each direction (standard regional)
- **Key value:** lowest latency and highest requests-per-second of any
  S3 storage class — purpose-built for latency-sensitive and
  high-throughput workloads where single-AZ placement is acceptable

## Application code patterns

### S3 SDK with directory bucket (Python / boto3)

```python
import boto3

# The SDK auto-resolves the Zonal endpoint from the bucket name format
s3 = boto3.client("s3", region_name="us-east-1")

# Put object into directory bucket
s3.put_object(
    Bucket="my-app-data--use1-az1--x-s3",
    Key="cache/shard-001.dat",
    Body=payload
)

# Get object from directory bucket
resp = s3.get_object(
    Bucket="my-app-data--use1-az1--x-s3",
    Key="cache/shard-001.dat"
)
body = resp["Body"].read()
```

### Latency probe (bash)

```bash
# From compute in the SAME AZ as the directory bucket
# Expected: single-digit milliseconds
time aws s3 ls s3://my-app-data--use1-az1--x-s3/ --region us-east-1

# From compute in a DIFFERENT AZ (for comparison)
# Expected: 10-50ms, plus cross-AZ transfer fees
time aws s3 ls s3://my-app-data--use1-az1--x-s3/ --region us-east-1
```

If the latency probe shows >10ms consistently, verify:
1. The compute instance is in the same AZ as the bucket (check AZ ID)
2. The SDK is not overriding to a regional endpoint
3. There is no VPC endpoint proxy that routes to a regional endpoint
