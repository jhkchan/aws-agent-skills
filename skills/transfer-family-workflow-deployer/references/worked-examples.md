# Worked examples — transfer-family-workflow-deployer

Moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Expert heuristic: session policy for per-user S3 scoping

A baseline model says "attach an IAM role with S3 permissions." The
correct heuristic recognizes that the session policy is the per-user
scoping mechanism.

```text
Per-user S3 scoping model:
  IAM role (assumed by Transfer Family on behalf of the user):
    ├── Defines MAXIMUM permissions (e.g., s3:GetObject, s3:PutObject)
    └── Attached to each user via create-user --role

  Session policy (applied at connection time):
    ├── Scopes the IAM role to specific S3 paths
    ├── Effective permissions = IAM role INTERSECT session policy
    └── Without session policy → user gets FULL IAM role permissions (RISK)

  Example:
    IAM role: s3:GetObject, s3:PutObject on all buckets
    Session policy: s3:GetObject, s3:PutObject on my-bucket/home/alice/*
    Effective: s3:GetObject, s3:PutObject on my-bucket/home/alice/*

  Without session policy:
    Effective: s3:GetObject, s3:PutObject on ALL buckets (SECURITY RISK)
```

**Key implication:** ALWAYS attach a session policy to every Transfer
Family user. The session policy is the only mechanism that scopes
each user to their own home directory. Without it, a user can access
any S3 path the IAM role permits.
## Expert heuristic: managed workflow for file landing zone automation

A managed workflow turns SFTP from a passive file store into an active
data pipeline. Every file upload triggers a Step Functions execution.

```text
Managed workflow pipeline (per file upload):
  1. File arrives via SFTP → lands in S3 (home directory)
  2. Transfer Family triggers the managed workflow
  3. Step Functions executes the workflow steps:
     ├── Pre-processing (optional): virus scan, format validation
     │   → if fails: quarantine file, notify user
     │   → if passes: continue
     4. File is available in S3
     5. Post-processing: transform, route, trigger downstream
        ├── Copy to data lake bucket
        ├── Trigger Lambda for ETL
        ├── Send SNS notification
        └── Move to archive bucket

  Workflow definition (JSON):
    Steps:
      - Type: COPY | DELETE | TAG | CUSTOM
      - Destination: s3://data-lake/processed/${originalName}
      - OnException: send SNS, retry 3x
```

**Key implication:** managed workflows are the mechanism for building
a file landing zone on Transfer Family. Without a workflow, files land
in S3 and require manual intervention or a separate event-driven
pipeline. With a workflow, the entire processing chain is automated
and visible in Step Functions execution history.
## Step-by-step CLI sequences

### Step 4 — VPC, subnets, security groups

```bash
aws transfer create-server \
  --protocols SFTP \
  --endpoint-type VPC_ENDPOINT \
  --endpoint-details \
    VpcId=vpc-aaa11122,\
    SubnetIds=subnet-aaa,subnet-bbb,\
    SecurityGroupIds=sg-sftp
```
### Step 5 — Route 53 hosted zone DNS

```bash
# Get the server endpoint
SERVER_ENDPOINT=$(aws transfer describe-server --server-id s-xxx \
  --query 'Server.EndpointDetails.Address' --output text)

# Create a CNAME record in Route 53
aws route53 change-resource-record-sets \
  --hosted-zone-id Z111111XXXX \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "sftp.example.com",
        "Type": "CNAME",
        "TTL": 60,
        "ResourceRecords": [{"Value": "'"$SERVER_ENDPOINT"'"}]
      }
    }]
  }'
```
### Step 6 — User home directory mapping

```bash
aws transfer create-user \
  --server-id s-xxx \
  --user-name alice \
  --role arn:aws:iam::123456789012:role/TransferFamilyS3 \
  --home-directory-type LOGICAL \
  --home-directory-mappings \
    Entry=/uploads,Target=/my-bucket/home/alice/uploads \
    Entry=/downloads,Target=/shared-bucket/distributions
```
### Step 7 — IAM role and session policy

**IAM role trust policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "transfer.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

**Session policy (per-user S3 scoping):**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:ListBucket"],
    "Resource": "arn:aws:s3:::my-bucket",
    "Condition": {
      "StringLike": {"s3:prefix": ["home/alice/*"]}
    }
  }, {
    "Effect": "Allow",
    "Action": ["s3:GetObject", "s3:PutObject"],
    "Resource": "arn:aws:s3:::my-bucket/home/alice/*"
  }]
}
```

```bash
aws transfer create-user \
  --server-id s-xxx \
  --user-name alice \
  --role arn:aws:iam::123456789012:role/TransferFamilyS3 \
  --session-policy file://session-policy-alice.json
```
### Step 8 — Server host key and trusted host keys

```bash
# Create server with a custom host key
aws transfer create-server \
  --protocols SFTP \
  --host-key file://server_host_key_rsa
```
### Step 9 — AS2 connectors

```bash
aws transfer create-connector \
  --url "https://partner.example.com/as2" \
  --as2-config \
    Compression=ZLIB,EncryptionAlgorithm=AES256_CBC,\
    SigningAlgorithm=SHA256,MdnResponse=SYNC,\
    LocalProfileId=local-profile-xxx,PartnerProfileId=partner-profile-yyy
```
### Step 10 — Managed workflows

```bash
# Create a managed workflow
aws transfer create-workflow \
  --description "File landing zone pipeline" \
  --steps \
    Type=COPY,\
    CopyStepDetails={DestinationFileLocation={Bucket=processed-data,Key=landing/},Name=CopyToDataLake},\
    Type=TAG,\
    TagStepDetails={Tags=[{Key=Status,Value=Processed}]} \
  --on-exception-steps \
    Type=TAG,\
    TagStepDetails={Tags=[{Key=Status,Value=Failed}]}
```

Attach the workflow to the Transfer server:

```bash
aws transfer update-server \
  --server-id s-xxx \
  --workflow-id w-xxx
```
### Step 11 — Structured JSON logging and CloudWatch

```bash
# Enable structured logging
aws transfer create-server \
  --protocols SFTP \
  --logging-role arn:aws:iam::123456789012:role/TransferFamilyLogging \
  --structured-log-destinations arn:aws:logs:us-east-1:123456789012:log-group:/aws/transfer/sftp
```
