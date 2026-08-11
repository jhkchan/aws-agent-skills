# Provisioning CLI Commands — S3 Access Points Deployer

Full copy-pasteable CLI command sequence for the 9-step provisioning
procedure. Variables to substitute: `<BUCKET>`, `<ACCOUNT_ID>`,
`<REGION>`, `<AP_NAME>`, `<VPC_ID>`, `<ROUTE_TABLE_ID>`, `<ROLE_ARN>`,
`<PREFIX>`, `<OLAP_NAME>`, `<FUNC_ARN>`, `<MRAP_NAME>`, `<BUCKET_A>`,
`<BUCKET_B>`, `<FOREIGN_ACCOUNT>`, `<OUTPOST_ID>`.

## Step 0: Prerequisites check

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)
echo "Account: $ACCOUNT_ID  Region: $REGION"

# Bucket exists and meets baseline
aws s3api get-public-access-block --bucket <BUCKET>
aws s3api get-bucket-encryption --bucket <BUCKET>
aws s3api get-bucket-versioning --bucket <BUCKET>

# (VPC origin) VPC exists
aws ec2 describe-vpcs --vpc-ids <VPC_ID> --query 'Vpcs[0].VpcId' --output text

# (VPC origin) Check for an existing S3 gateway endpoint
aws ec2 describe-vpc-endpoints \
  --filters Name=vpc-id,Values=<VPC_ID> Name=service-name,Values=com.amazonaws.<REGION>.s3 \
  --query 'VpcEndpoints[0].VpcEndpointId' --output text
```

## Step 1: Bucket baseline

See `s3-secure-bucket-deployer` for the full bucket baseline. Confirm
BPA (account + bucket), SSE, and versioning before proceeding.

```bash
aws s3api get-public-access-block --bucket <BUCKET>
aws s3api get-bucket-encryption --bucket <BUCKET>
```

## Step 2: Network origin decision

No CLI. Document the choice (`Internet` or `VPC`) and, if VPC, capture
the VPC ID and route table ID.

## Step 3: VPC gateway endpoint + policy (VPC origin only)

Create the endpoint with an AP-restrictive policy (see
`references/access-point-policy-examples.md` section 4).

```bash
aws ec2 create-vpc-endpoint \
  --vpc-id <VPC_ID> \
  --service-name com.amazonaws.<REGION>.s3 \
  --route-table-ids <ROUTE_TABLE_ID> \
  --vpc-endpoint-type Gateway \
  --policy-document file://vpce-policy.json
```

For private DNS on the S3 interface endpoint (optional, for in-VPC DNS
resolution of the S3 regional endpoint):

```bash
aws ec2 create-vpc-endpoint \
  --vpc-id <VPC_ID> \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.<REGION>.s3 \
  --subnet-ids <SUBNET_ID> \
  --security-group-ids <SG_ID> \
  --private-dns-enabled
```

## Step 4: Create the access point

```bash
# Internet origin
aws s3control create-access-point \
  --account-id <ACCOUNT_ID> \
  --name <AP_NAME> \
  --bucket <BUCKET>

# VPC origin
aws s3control create-access-point \
  --account-id <ACCOUNT_ID> \
  --name <AP_NAME> \
  --bucket <BUCKET> \
  --vpc-configuration VpcId=<VPC_ID>
```

Verify and capture the alias:

```bash
aws s3control get-access-point --account-id <ACCOUNT_ID> --name <AP_NAME> \
  --query 'Alias' --output text
```

## Step 5: Access point policy

```bash
aws s3control put-access-point-policy \
  --account-id <ACCOUNT_ID> \
  --name <AP_NAME> \
  --policy file://ap-policy.json
```

## Step 6: Through-AP-only bucket-policy Deny (REQUIRED for VPC-only)

Append the `RequireThroughAccessPoint` statement to the existing bucket
policy. Read the current policy first to avoid clobbering.

```bash
aws s3api get-bucket-policy --bucket <BUCKET> --query Policy --output text > current-policy.json
# Merge in the RequireThroughAccessPoint statement (see references section 3)
aws s3api put-bucket-policy --bucket <BUCKET> --policy file://merged-policy.json
```

## Step 7: Per-AP Block Public Access (VPC origin)

```bash
aws s3control put-access-point-public-access-block \
  --account-id <ACCOUNT_ID> \
  --name <AP_NAME> \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

## Step 8a: Object Lambda access point

```bash
# Transform function must exist with reserved-concurrency + OLAP invoke grant
aws lambda put-function-concurrency \
  --function-name <FUNC_NAME> \
  --reserved-concurrent-executions 50

aws s3control create-access-point-for-object-lambda \
  --account-id <ACCOUNT_ID> \
  --name <OLAP_NAME> \
  --configuration \
    SupportingAccessPoint=arn:aws:s3:<REGION>:<ACCOUNT_ID>:accesspoint/<AP_NAME>,\
    TransformationConfigurations='[{Action=GetObject,ContentTransformation=AWSLambda:{FunctionArn=<FUNC_ARN>}}]'
```

## Step 8b: Multi-Region Access Point

```bash
aws s3control create-multi-region-access-point \
  --account-id <ACCOUNT_ID> \
  --details Name=<MRAP_NAME>,Regions='[{Bucket=arn:aws:s3:::<BUCKET_A>},{Bucket=arn:aws:s3:::<BUCKET_B>}]'

# Async — poll until Status=READY
aws s3control get-multi-region-access-point \
  --account-id <ACCOUNT_ID> \
  --name <MRAP_NAME>
```

## Step 8c: Cross-account access point

Bucket owner grants `s3:CreateAccessPoint`:

```bash
aws s3api put-bucket-policy --bucket <BUCKET> --policy file://cross-account-delegation.json
```

Foreign account then runs `create-access-point` as in Step 4. Verify
the foreign-owned AP ARN and add a containment statement (see
references section 5).

## Step 8d: Alias (no create step)

The alias is auto-generated; verify and use directly:

```bash
aws s3control get-access-point --account-id <ACCOUNT_ID> --name <AP_NAME> \
  --query 'Alias' --output text
```

## Step 8e: S3 on Outposts access point

```bash
aws s3outposts create-access-point \
  --container-arn arn:aws:s3-outposts:<REGION>:<ACCOUNT_ID>:outpost/<OUTPOST_ID>/bucket/<BUCKET> \
  --name <AP_NAME>

aws s3outposts list-access-points \
  --container-arn arn:aws:s3-outposts:<REGION>:<ACCOUNT_ID>:outpost/<OUTPOST_ID>/bucket/<BUCKET>
```

## Step 9: Verification

```bash
aws s3control get-access-point --account-id <ACCOUNT_ID> --name <AP_NAME>
aws s3control get-access-point-policy --account-id <ACCOUNT_ID> --name <AP_NAME>
aws s3control get-access-point-public-access-block --account-id <ACCOUNT_ID> --name <AP_NAME>
aws s3api get-bucket-policy --bucket <BUCKET>
aws ec2 describe-vpc-endpoints --filters Name=vpc-id,Values=<VPC_ID>

# Object Lambda only
aws s3control get-access-point-configuration-for-object-lambda \
  --account-id <ACCOUNT_ID> --name <OLAP_NAME>

# MRAP only
aws s3control get-multi-region-access-point \
  --account-id <ACCOUNT_ID> --name <MRAP_NAME>

# Outposts only
aws s3outposts list-access-points \
  --container-arn arn:aws:s3-outposts:<REGION>:<ACCOUNT_ID>:outpost/<OUTPOST_ID>/bucket/<BUCKET>
```
