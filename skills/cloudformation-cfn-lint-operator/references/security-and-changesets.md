# Security Scanning and ChangeSets — CloudFormation cfn-lint Operator

Deep reference on cfn-nag security scanning (rule catalog, severity
levels, suppression, false positive management), ChangeSet creation
and interpretation (Action/Replacement fields, risk assessment,
execution vs deletion), drift detection mechanics, and stack policy
enforcement. Loaded on demand by the skill — kept out of the main
SKILL.md body so the operation procedure stays scannable.

## cfn-nag security scanning deep dive

### Rule catalog by category

**IAM rules:**

| Rule ID | Severity | Description |
|---|---|---|
| F1 | CRITICAL | IAM policy with `Resource: "*"` |
| F2 | CRITICAL | IAM policy with `Action: "*"` |
| F3 | CRITICAL | IAM role with wildcard trust policy |
| F4 | WARNING | IAM managed policy with `Resource: "*"` (even scoped actions) |
| F5 | WARNING | IAM role with `AdministratorAccess` |
| F6 | WARNING | Lambda event source mapping with excessive permissions |
| F77 | CRITICAL | KMS key with wildcard key policy principal |

**S3 rules:**

| Rule ID | Severity | Description |
|---|---|---|
| W41 | CRITICAL | S3 bucket without server-side encryption |
| W42 | WARNING | S3 bucket without versioning enabled |
| W43 | WARNING | S3 bucket without access logging |
| W51 | WARNING | S3 bucket with no bucket policy (open access depends on ACL) |
| F14 | CRITICAL | S3 bucket with public read ACL |
| F15 | CRITICAL | S3 bucket with public write ACL |

**Security group rules:**

| Rule ID | Severity | Description |
|---|---|---|
| F1000 | CRITICAL | SG ingress from `0.0.0.0/0` to port 22 (SSH) |
| F1001 | CRITICAL | SG ingress from `0.0.0.0/0` to port 3389 (RDP) |
| F1002 | WARNING | SG ingress from `0.0.0.0/0` to any port |
| F1003 | WARNING | SG egress to `0.0.0.0/0` (open egress) |
| W9 | WARNING | SG ingress to port 0 (all ports) |

**RDS/DynamoDB/EFS rules:**

| Rule ID | Severity | Description |
|---|---|---|
| W40 | CRITICAL | RDS instance with public access (`PubliclyAccessible: true`) |
| W73 | CRITICAL | RDS instance without encryption at rest |
| W74 | WARNING | RDS instance with backup retention = 0 |
| W39 | WARNING | DynamoDB table without point-in-time recovery |
| W83 | WARNING | EFS filesystem without encryption at rest |

### Suppressing false positives

Not all cfn-nag findings are actionable. For example, a log delivery
bucket may intentionally not have encryption at the bucket level
because encryption is applied via organizational-level bucket
policies. Suppress with documented justification:

```yaml
Resources:
  LogDeliveryBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub "${AWS::StackName}-logs"
    Metadata:
      cfn_nag:
        rules_to_suppress:
          - id: W41
            reason: "Log delivery bucket — SSE-KMS applied via org-level bucket policy"
          - id: W43
            reason: "Access logging not required for the log bucket itself"
```

**Suppression discipline:**
- Always provide a `reason` that explains WHY the finding is not
  applicable.
- Review suppressions periodically — the justification may become
  stale if the infrastructure evolves.
- Track suppressions in code review — suppressions should be
  approved, not self-authorized.

### Running cfn-nag on a directory

```bash
# Scan all templates in a directory
cfn_nag_scan --input-path ./templates/

# Output as JSON with full finding details
cfn_nag_scan --input-path template.yaml --output-format json

# Treat warnings as failures (for strict pipelines)
cfn_nag_scan --input-path template.yaml --fail-on-warnings
```

### Pipeline gate logic

```bash
# Block on CRITICAL findings only (allow warnings)
cfn_nag_scan --input-path template.yaml
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
  echo "cfn-nag found CRITICAL findings — blocking deployment"
  exit 1
fi

# Block on both CRITICAL and WARNING findings
cfn_nag_scan --input-path template.yaml --fail-on-warnings
```

## ChangeSet deep dive

### ChangeSet creation flow

```text
1. Create ChangeSet (create-change-set)
   → CloudFormation compares the new template against the current stack
   → Generates a list of resource changes
   → Status: CREATE_IN_PROGRESS → CREATE_COMPLETE (or FAILED)

2. Review ChangeSet (describe-change-set)
   → Inspect each resource change (Action, Replacement, Scope)
   → Identify high-risk changes (Replacement: True on stateful resources)

3. Decision: Execute or Delete
   → Execute (execute-change-set): applies the changes
   → Delete (delete-change-set): discards the changes
```

### ChangeSet detail: the Scope field

The `Scope` field in a ChangeSet resource change tells you WHICH
properties of a resource are changing:

| Scope | Meaning | Risk |
|---|---|---|
| Properties | One or more properties are changing | Depends on Replacement field |
| Metadata | Only Metadata is changing | Low — no resource impact |
| Tags | Only tags are changing | Low — no resource impact |
| Tags,Properties | Tags and properties changing | Depends on Replacement field |

### Identifying immutable property changes

Properties that trigger replacement vary by resource type. Common
examples:

| Resource Type | Immutable properties (trigger replacement) |
|---|---|
| AWS::RDS::DBInstance | AllocatedStorage (downgrade), DBInstanceClass, Engine, MasterUsername |
| AWS::EC2::Instance | InstanceType, ImageId, SubnetId, AvailabilityZone |
| AWS::S3::Bucket | BucketName |
| AWS::DynamoDB::Table | TableName, AttributeDefinitions, KeySchema |
| AWS::IAM::Role | RoleName |
| AWS::EFS::FileSystem | Encrypted (cannot change after creation) |

**Before executing a ChangeSet with Replacement: True on a stateful
resource, verify:**
1. The resource has `DeletionPolicy: Retain` (prevents data loss).
2. A backup exists (snapshot or export).
3. The replacement is intentional (not an accidental property change).
4. Application downtime is acceptable during the replacement.

### ChangeSet with nested stacks

For stacks with nested children, the ChangeSet shows changes at the
PARENT level. Nested stack changes appear as `Action: Modify` on the
`AWS::CloudFormation::Stack` resource. To see changes WITHIN the
nested stack, create a ChangeSet on the NESTED stack directly (using
the nested stack's ID, not name).

### Drift detection deep dive

```bash
# Start drift detection
DETECTION_ID=$(aws cloudformation detect-stack-drift \
  --stack-name my-stack \
  --query 'StackDriftDetectionId' --output text --region us-east-1)

# Poll for completion
while true; do
  STATUS=$(aws cloudformation describe-stack-drift-detection-status \
    --stack-drift-detection-id "$DETECTION_ID" \
    --query 'DetectionStatus' --output text --region us-east-1)
  if [ "$STATUS" = "DETECTION_COMPLETE" ]; then break; fi
  sleep 5
done

# Get overall drift status
aws cloudformation describe-stack-resource-drifts \
  --stack-name my-stack \
  --region us-east-1 --output table
```

**Resource drift statuses:**

| Status | Meaning |
|---|---|
| IN_SYNC | Resource matches template |
| MODIFIED | Resource properties differ from template |
| DELETED | Resource was deleted outside CloudFormation |
| NOT_CHECKED | Resource type does not support drift detection |

**Not all resource types support drift detection.** Check the
CloudFormation documentation for the supported types list. Common
unsupported types include `AWS::CloudFront::Distribution` (added
recently) and some third-party resource types.

## Stack policy deep dive

### Stack policy vs DeletionPolicy

| Protection | Stack policy | DeletionPolicy |
|---|---|---|
| Prevents UPDATE | YES | NO |
| Prevents DELETE (stack deletion) | NO | YES (Retain) |
| Prevents DELETE (resource removal from template) | NO | YES (Retain) |
| Applied at | Stack level | Resource level |
| Scope | All resources or filtered by type | Per-resource |

**For full protection:** use BOTH a stack policy (prevents accidental
updates) and `DeletionPolicy: Retain` (prevents deletion).

### Stack policy with resource override

Sometimes you need to update a protected resource. Use a resource-
level override in the stack policy:

```bash
# Temporarily allow updates to a protected resource
aws cloudformation set-stack-policy \
  --stack-name my-stack \
  --stack-policy-body file://temporary-allow-policy.json \
  --region us-east-1

# After the update, restore the protective policy
aws cloudformation set-stack-policy \
  --stack-name my-stack \
  --stack-policy-body file://protective-policy.json \
  --region us-east-1
```

**Security note:** always restore the protective policy immediately
after the update. Leaving a permissive policy defeats the purpose.
