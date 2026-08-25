# Diagnostic Commands — S3 Access Denied Troubleshooter

Pre-flight, per-step probe, safety-check, and remediation CLI listings moved verbatim from SKILL.md. Loaded on demand.

## Pre-flight — account-wide commands

```bash
# 1. Identify the caller (who is making the denied request?)
aws sts get-caller-identity --profile <p> --output json

# 2. CloudTrail lookup for the exact denied event
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=GetObject \
  --start-time $(date -d '-1 hour' +%s) --end-time $(date +%s) \
  --output json | \
  jq '.Events[] | select(.CloudTrailEvent | contains("AccessDenied"))'

# 3. Bucket policy
aws s3api get-bucket-policy --bucket <bucket> --output json 2>/dev/null || \
  echo "No bucket policy"

# 4. Bucket ownership controls
aws s3api get-bucket-ownership-controls --bucket <bucket> --output json 2>/dev/null || \
  echo "No ownership controls (defaults apply)"

# 5. Block Public Access settings
aws s3api get-public-access-block --bucket <bucket> --output json 2>/dev/null

# 6. KMS key (if the bucket has a default encryption config)
aws s3api get-bucket-encryption --bucket <bucket> --output json 2>/dev/null | \
  jq '.ServerSideEncryptionConfiguration'

# 7. VPC endpoints for S3 (if the caller is VPC-attached)
aws ec2 describe-vpc-endpoints \
  --filters Name=service-name,Values=com.amazonaws.<region>.s3 \
  --output json | jq '.VpcEndpoints[] | {VpcEndpointId, Policy, State}'
```

## Step 1 — SCP layer probe commands

```bash
# List all SCPs attached to the caller's account
aws organizations list-policies-for-target \
  --target-id <account-id> \
  --filter SERVICE_CONTROL_POLICY \
  --output json

# Get the content of each SCP
aws organizations describe-policy \
  --policy-id <policy-id> --output json | \
  jq '.Policy.Content | fromjson'
```

## Step 2 — IAM simulation probe

```bash
# Simulate the caller's effective permissions
aws iam simulate-principal-policy \
  --policy-source-arn <caller-arn> \
  --action-names s3:GetObject \
  --resource-arns arn:aws:s3:::<bucket>/<key> \
  --output json --profile <p>
```

## Step 3 — permission boundary probes

```bash
aws iam get-role --role-name <role-name> --output json | \
  jq '.Role.PermissionsBoundary'
```

If a permissions boundary exists, simulate with it:

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <caller-arn> \
  --action-names s3:GetObject \
  --resource-arns arn:aws:s3:::<bucket>/<key> \
  --permissions-boundary-policy-list <boundary-policy-json> \
  --output json --profile <p>
```

## Step 4 — bucket policy probe

```bash
aws s3api get-bucket-policy --bucket <bucket> --output json | \
  jq '.Policy | fromjson'
```

## Step 5 — KMS gate probes

```bash
# Check the bucket's default encryption
aws s3api get-bucket-encryption --bucket <bucket> --output json | \
  jq '.ServerSideEncryptionConfiguration'

# If SSE-KMS with a customer-managed key:
aws kms describe-key --key-id <key-arn> --output json | \
  jq '.KeyMetadata.{KeyManager, KeyState, Enabled}'

aws kms get-key-policy --key-id <key-arn> --policy-name default --output json | \
  jq '.Policy | fromjson'
```

Simulate the caller's KMS permissions:

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <caller-arn> \
  --action-names kms:Decrypt \
  --resource-arns <key-arn> \
  --output json --profile <p>
```

## Step 6 — object ownership probes

```bash
aws s3api get-bucket-ownership-controls --bucket <bucket> --output json 2>/dev/null

aws s3api get-object-acl --bucket <bucket> --key <key> --output json
```

## Step 7 — VPC endpoint policy probe

```bash
aws ec2 describe-vpc-endpoints \
  --filters Name=service-name,Values=com.amazonaws.<region>.s3 \
  --output json | \
  jq '.VpcEndpoints[] | {VpcEndpointId, Policy, State}'
```

## Step 9 — Block Public Access probe

```bash
aws s3api get-public-access-block --bucket <bucket> --output json
```

## Step 10 — Object Lock probes

```bash
aws s3api get-object-lock-configuration --bucket <bucket> --output json 2>/dev/null

aws s3api get-object-retention --bucket <bucket> --key <key> --output json 2>/dev/null

aws s3api get-object-legal-hold --bucket <bucket> --key <key> --output json 2>/dev/null
```

## Step 11 — Object Lambda probe

```bash
aws s3control get-access-point-configuration-for-object-lambda \
  --account-id <account-id> \
  --name <access-point-name> --output json
```

## Step 12 — ownership controls probe

```bash
aws s3api get-bucket-ownership-controls --bucket <bucket> --output json
```

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`put-bucket-policy`, `put-role-policy`, `put-public-access-block`,
  `put-bucket-ownership-controls`, `delete-object-retention`), emit
  and await operator approval. Do NOT execute the CLI until the
  operator confirms.

- **Read-only first.** Every probe in the diagnostic tree is
  read-only (`get-bucket-policy`, `get-object-acl`, `simulate-principal-policy`,
  `lookup-events`, `describe-key`, `describe-vpc-endpoints`). Do not
  perform state-changing operations as diagnostic probes.

- **Bucket policy changes** affect every consumer of the bucket.
  Tighten policy gradually; test with `simulate-principal-policy`
  before applying.

- **KMS key policy changes** affect every service that uses the key.
  Never remove a key policy statement without confirming no S3 bucket,
  Lambda function, or other service depends on it.

- **Object Lock changes** are irreversible for COMPLIANCE-mode objects.
  Never attempt to bypass retention on a COMPLIANCE-mode object.

- **Block Public Access changes** at the account level affect all
  buckets in the account. Always scope to the bucket level unless
  the account-level setting is intentionally global.

## Remediation guidance (per root cause)

### For SCP_DENY

```bash
# Detach or update the SCP at the org/OU level
aws organizations detach-policy \
  --policy-id <policy-id> --target-id <org-unit-id>
# Or update the SCP to scope the Deny narrower
aws organizations update-policy \
  --policy-id <policy-id> \
  --content '<narrower JSON>'
```

### For IMPLICIT_DENY_IAM

Add the minimum-scope permission to the caller's identity-based policy:

```bash
aws iam put-role-policy --role-name <role-name> \
  --policy-name <name> \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"s3:GetObject","Resource":"arn:aws:s3:::<bucket>/<prefix>/*"}]}'
```

### For EXPLICIT_DENY_BUCKET_POLICY

Identify the Deny statement in the bucket policy and remove or scope
it narrower. Re-test with `simulate-principal-policy`.

### For KMS_KEY_POLICY

Add `kms:Decrypt` on the key ARN to the caller's IAM policy:

```bash
aws iam put-role-policy --role-name <role-name> \
  --policy-name kms-decrypt \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"kms:Decrypt","Resource":"<key-arn>"}]}'
```

If the key policy itself does not grant the caller's account, update
the key policy:

```bash
aws kms put-key-policy --key-id <key-arn> \
  --policy-name default \
  --policy '<JSON with the caller account in the Principal>'
```

### For CROSS_ACCOUNT_MISSING_BUCKET_POLICY

Add a bucket policy statement allowing the caller's account:

```bash
aws s3api put-bucket-policy --bucket <bucket> \
  --policy '{"Version":"2012-10-17","Statement":[{"Sid":"CrossAccount","Effect":"Allow","Principal":{"AWS":"arn:aws:iam::<caller-account>:root"},"Action":"s3:GetObject","Resource":"arn:aws:s3:::<bucket>/<prefix>/*"}]}'
```

### For OBJECT_OWNERSHIP

Enable bucket owner enforced:

```bash
aws s3api put-bucket-ownership-controls --bucket <bucket> \
  --ownership-controls Rules=[{ObjectOwnership=BucketOwnerEnforced}]
```

For existing objects owned by the uploader, use S3 Batch Operations to
copy in-place:

```bash
aws s3control create-job \
  --account-id <account-id> \
  --operation '{"S3PutObjectCopy":{"BucketReference":{"Bucket":"<bucket>"}}}' \
  --manifest '{"Spec":{"Format":"S3BatchOperations_CSV_20180820","Fields":["Bucket","Key"]},"Location":{"Bucket":"<manifest-bucket>","Key":"manifest.csv"}}' \
  --report '{"Bucket":"<report-bucket>","Format":"Report_CSV_20180820","Enabled":true}' \
  --role-arn <batch-role-arn>
```

### For VPC_ENDPOINT_POLICY

Update the endpoint policy to allow the denied action:

```bash
aws ec2 modify-vpc-endpoint --vpc-endpoint-id <vpce-id> \
  --policy-document '<JSON allowing the S3 action>'
```

### For PRESIGNED_URL_EXPIRED

Generate a new presigned URL with sufficient expiry. If the caller
needs long-lived access, use IAM credentials directly instead of
presigned URLs.

### For BLOCK_PUBLIC_ACCESS

If public access is intentionally required (e.g., static website
hosting), disable the relevant Block Public Access setting:

```bash
aws s3api put-public-access-block --bucket <bucket> \
  --public-access-block-configuration BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false
```

### For OBJECT_LOCK_RETENTION

For GOVERNANCE-mode objects with the `s3:BypassGovernanceRetention`
permission:

```bash
aws s3api delete-object --bucket <bucket> --key <key> \
  --bypass-governance-retention
```

For COMPLIANCE-mode objects: no bypass is possible. Wait for the
retention period to expire.

### For PERMISSION_BOUNDARY

Update the permission boundary to allow the S3 action:

```bash
aws iam put-role-permissions-boundary \
  --role-name <role-name> \
  --permissions-boundary <policy-arn>
```

Or attach a new boundary policy that includes the S3 action.

### For OBJECT_LAMBDA_ROUTING

Update the caller's SDK to use the Object Lambda ARN:

```text
arn:aws:s3-object-lambda:<region>:<account>:accesspoint/<name>/key
```

### For REQUEST_ACCOUNT_MISMATCH

Include the `x-amz-expected-bucket-owner` header in the request with
the bucket owner's account ID. Most SDKs support this via a request
parameter.
