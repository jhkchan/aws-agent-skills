# Diagnostic Commands — S3 Access Troubleshooter

Load-on-demand branch evidence and probe detail, moved verbatim from
SKILL.md. Each Step below is the FULL original branch text; SKILL.md
keeps the branch titles and Output/verdict lines.

## Step 1: GetObject AccessDenied diagnostic path

### Step 1: GetObject AccessDenied diagnostic path

Walk these in order; the first match is the root cause.

1. **Identity policy missing `s3:GetObject` on the OBJECT ARN.**
   - Check via `aws iam simulate-principal-policy --action-names
     s3:GetObject --resource-arns arn:aws:s3:::bucket/key`.
   - Most common cause. Verify the policy uses
     `arn:aws:s3:::bucket-name/*` (object ARN), not
     `arn:aws:s3:::bucket-name` (bucket ARN — wrong for GetObject).
   - **Output:** ROOT_CAUSE_FOUND, layer = identity-based, missing
     `s3:GetObject` on object ARN.

2. **Bucket policy explicit `Deny` on `s3:GetObject`.**
   - Read bucket policy: `aws s3api get-bucket-policy --bucket <name>`.
   - Look for `Effect: Deny` with `Action: s3:GetObject` or
     `NotAction` including GetObject. Check the `Condition` — `aws:SecureTransport:
     false` (TLS enforcement), `aws:SourceIp` (IP allowlist),
     `aws:SourceVpce` (VPCe enforcement).
   - **Output:** ROOT_CAUSE_FOUND, layer = bucket policy Deny, statement
     Sid + matched condition keys.

3. **KMS key policy does not grant `kms:Decrypt` to the caller.**
   - Determine the bucket's encryption:
     `aws s3api get-bucket-encryption --bucket <name>`. If SSE-KMS with a
     customer-managed key, KMS is a separate gate.
   - Read the key policy:
     `aws kms describe-key --key-id <key-id>` and
     `aws kms get-key-policy --key-id <key-id> --policy-name default`.
   - For same-account: the key policy MUST grant `kms:Decrypt` to the
     caller. For cross-account: see Step 4.
   - ALSO verify the identity policy has `kms:Decrypt` on the key ARN.
   - **Output:** ROOT_CAUSE_FOUND, layer = KMS key policy, missing
     `kms:Decrypt` grant.

4. **Block Public Access blocking an otherwise-valid public policy.**
   - If the bucket policy or ACL grants public access AND BPA is enabled
     at the account or bucket level, S3 silently denies the public
     request. The error is `AccessDenied` with no hint about BPA.
   - Check both levels:
     `aws s3control get-public-access-block --account-id <acct>` and
     `aws s3api get-public-access-block --bucket <name>`.
   - All four settings must be False for public access to work:
     `BlockPublicAcls`, `IgnorePublicAcls`, `BlockPublicPolicy`,
     `RestrictPublicBuckets`. Account-level BPA overrides bucket-level.
   - **Output:** ROOT_CAUSE_FOUND, layer = BPA (account or bucket),
     specific settings blocking.

5. **Object Ownership = `BucketOwnerEnforced` blocking cross-account
   writers.**
   - If the caller is in a different account than the bucket owner AND
     the bucket's Object Ownership is `BucketOwnerEnforced`, ACLs are
     disabled. Cross-account writers cannot use ACL-based ownership
     transfer — they MUST include `x-amz-acl: bucket-owner-full-control`
     in the upload AND the bucket policy must Allow it.
   - `aws s3api get-bucket-ownership-controls --bucket <name>`.
   - **Output:** ROOT_CAUSE_FOUND, layer = Object Ownership /
     `BucketOwnerEnforced`, ACLs disabled.

6. **VPC endpoint policy restricting S3 access.**
   - If the caller is in a VPC with a VPC endpoint for S3 (Gateway or
     Interface), the endpoint's policy is an independent gate that can
     deny requests even when all IAM/S3 policies allow.
   - The CloudTrail event shows AccessDenied with no hint about the VPC
     endpoint. The diagnostic is to bypass the endpoint (route over
     internet or a different endpoint) and see if the call succeeds.
   - **Output:** ROOT_CAUSE_FOUND, layer = VPC endpoint policy.

7. **CloudFront OAC misconfigured (origin is S3).**
   - If the caller is reaching S3 through CloudFront, the S3 bucket
     policy MUST grant `s3:GetObject` to the CloudFront OAC principal
     (`service:cloudfront.amazonaws.com` with the OAC ID in
     `aws:SourceArn` condition). The legacy OAI uses a different
     principal format.
   - Read the bucket policy and verify the CloudFront principal.
   - **Output:** ROOT_CAUSE_FOUND, layer = bucket policy CloudFront
     principal (OAC vs OAI mismatch).


## Step 2: PutObject AccessDenied diagnostic path

### Step 2: PutObject AccessDenied diagnostic path

1. **Identity policy missing `s3:PutObject` on the OBJECT ARN.**
   - Same shape as GetObject — verify object ARN (`bucket/*`).

2. **Bucket policy `Deny` enforcing SSE.**
   - Common pattern: bucket policy denies `s3:PutObject` when
     `s3:x-amz-server-side-encryption` is not `aws:kms` or `AES256`.
     Operators uploading without the SSE header get AccessDenied.
   - Read the bucket policy's Deny statements for
     `s3:x-amz-server-side-encryption` or
     `s3:x-amz-server-side-encryption-aws-kms-key-id`.
   - **Output:** ROOT_CAUSE_FOUND, layer = bucket policy SSE enforcement
     Deny.

3. **Missing `kms:GenerateDataKey`.**
   - SSE-KMS PutObject requires `kms:GenerateDataKey` on the key ARN in
     addition to `s3:PutObject` on the object. The KMS call is made by
     S3 on the caller's behalf.
   - Cross-account: BOTH the caller's identity policy AND the KMS key
     policy must allow. See Step 4.
   - **Output:** ROOT_CAUSE_FOUND, layer = KMS, missing
     `kms:GenerateDataKey`.

4. **Bucket full (capacity exhausted).**
   - Rare in standard buckets (no quota), but possible for S3 Directory
     Buckets (`/express-*`). The error message usually says "Bucket is
     full" but can appear as AccessDenied on misconfigured clients.
   - `aws s3 ls s3://<bucket> --recursive --human-readable --summarize`
     for size check.

5. **Object Lock retention / legal hold.**
   - An object under `ObjectLockRetention` (`COMPLIANCE` or `GOVERNANCE`)
     or `LegalHold` cannot be overwritten or deleted. `COMPLIANCE` mode
     cannot be bypassed even by root.
   - `aws s3api get-object-retention --bucket <b> --key <k>` and
     `aws s3api get-object-legal-hold --bucket <b> --key <k>`.
   - **Output:** ROOT_CAUSE_FOUND, layer = Object Lock retention /
     legal hold, mode and retain-until date.

6. **Object Ownership = `BucketOwnerEnforced` (cross-account write
   without bucket-owner-full-control ACL).**
   - Cross-account writers MUST include
     `x-amz-acl: bucket-owner-full-control` in the PutObject request.
     Without it, the upload may succeed but the object is owned by the
     writer's account — and `BucketOwnerEnforced` may reject the upload
     entirely if the bucket policy requires it.
   - **Output:** ROOT_CAUSE_FOUND, layer = Object Ownership /
     `BucketOwnerEnforced`, missing
     `x-amz-acl: bucket-owner-full-control`.


## Step 3: ListBucket AccessDenied diagnostic path

### Step 3: ListBucket AccessDenied diagnostic path

1. **Identity policy missing `s3:ListBucket` on the BUCKET ARN.**
   - The #1 cause. `s3:ListBucket` requires the bucket ARN
     (`arn:aws:s3:::bucket-name`), NOT the object ARN. Operators often
     write `s3:ListBucket` on `bucket/*` — that matches no resource.
   - **Output:** ROOT_CAUSE_FOUND, layer = identity-based, ARN shape
     wrong (object ARN used instead of bucket ARN).

2. **Prefix-scoped listing denied (conditional resources).**
   - For prefix-scoped ListBucket permission, the identity policy uses
     two Resource entries:
     ```json
     "Resource": [
       "arn:aws:s3:::bucket-name",
       "arn:aws:s3:::bucket-name/prefix/*"
     ]
     ```
   - The first grants ListBucket on the bucket ARN; the second grants
     GetObject on objects under `prefix/`. Listing outside the prefix
     fails with AccessDenied.
   - Verify both entries exist.

3. **Bucket policy Deny on `s3:ListBucket`.**
   - Same as GetObject Deny — read the policy, look for `Effect: Deny`
     with `Action: s3:ListBucket` or `NotAction`.

4. **KMS is NOT a factor for ListBucket.** ListBucket does not read
   object content — no KMS decrypt is invoked. KMS issues only affect
   object-level operations.


## Step 4: Cross-account S3 access diagnostic path

### Step 4: Cross-account S3 access diagnostic path

For cross-account calls (caller account ≠ bucket account), BOTH the
caller's identity-based policy AND the bucket's resource-based policy
must Allow the action. This is the intersection rule.

```
Same-account:   identity-based  ∪  bucket policy  (either Allows = grant)
Cross-account:  identity-based  ∩  bucket policy  (both must Allow)
```

Walk these in order:

1. **Verify identity policy (caller account) grants the action on the
   ARN.** Same ARN-shape rules as Steps 1-3 apply.

2. **Verify bucket policy (bucket account) grants the action to the
   caller principal ARN.**
   - Read: `aws s3api get-bucket-policy --bucket <name> --profile
     <bucket-acct>`.
   - The policy's `Principal.AWS` MUST include the caller's role ARN
     (`arn:aws:iam::<caller-acct>:role/<role>`). A `Principal: "*"` is
     not enough if BPA is enabled at either scope.
   - **Output:** ROOT_CAUSE_FOUND, layer = bucket policy missing
     cross-account principal.

3. **KMS key policy in BOTH accounts (for SSE-KMS).**
   - The KMS key is in the bucket's account. The key policy MUST grant
     `kms:Decrypt` (read) and `kms:GenerateDataKey` (write) to the
     caller's role ARN.
   - The caller's identity policy MUST ALSO grant `kms:Decrypt` /
     `kms:GenerateDataKey` on the key ARN. The intersection rule applies
     at KMS too.
   - `aws kms get-key-policy --key-id <key-id> --policy-name default
     --profile <bucket-acct>` — check for the caller's role ARN.
   - **Output:** ROOT_CAUSE_FOUND, layer = KMS key policy missing
     cross-account grant.

4. **Account-level BPA in the bucket account.**
   - Account-level BPA blocks public access regardless of bucket policy.
     For cross-account non-public access, BPA's `RestrictPublicBuckets`
     can still block a `Principal: "*"` policy if the caller is not
     authenticated — but cross-account IAM role access is not "public"
     and is not blocked by BPA directly.
   - However, BPA blocks public ACLs that were the original cross-account
     mechanism pre-2022. If the workflow uses ACL-based ownership
     transfer and BPA is on, the ACL is silently ignored.
   - **Output:** ROOT_CAUSE_FOUND, layer = account-level BPA, ACL-based
     cross-account workflow broken.

5. **KMS `aws:SourceAccount` chain.**
   - When S3 reads an object on behalf of a caller, the KMS call is made
     BY S3. A KMS key policy that requires
     `aws:SourceAccount: "<bucket-acct>"` evaluates the S3 service call's
     source account — which is the BUCKET's account, not the caller's.
     Operators writing this condition expecting it to mean "the caller's
     account" produce silent denies.
   - **Output:** ROOT_CAUSE_FOUND, layer = KMS key policy
     `aws:SourceAccount` chain, source account is bucket's account not
     caller's.

6. **VPC endpoint policy (cross-VPC or cross-account via TGW).**
   - If the caller is in a different VPC reaching the bucket through a
     VPC endpoint, the endpoint policy may restrict the principals or
     buckets allowed. Cross-account traffic through a shared VPC endpoint
     inherits the endpoint policy.


## Step 5: Presigned URL failure diagnostic path

### Step 5: Presigned URL failure diagnostic path

A presigned URL embeds the signing credential, signature, expiry, and
region. Any mismatch produces 403.

1. **URL expired.**
   - Decode the URL's `X-Amz-Date` (signing time) and `X-Amz-Expires`
     (validity seconds). The URL expires at `X-Amz-Date +
     X-Amz-Expires`.
   - Default max expiry: 7 days (604800 seconds) for IAM-user-signed
     URLs, 36 hours (129600) for STS-session-signed URLs, 1 hour for
     instance-role-signed URLs.
   - **Output:** ROOT_CAUSE_FOUND, layer = presigned URL expired.

2. **SigV4 credential scope / region mismatch.**
   - The URL's `X-Amz-Credential` includes `<key-id>/<date>/<region>/
     s3/aws4_request`. The region MUST match the bucket's region. A
     presigned URL for `us-east-1` used against a `us-west-2` bucket
     returns 403.
   - `aws s3api get-bucket-location --bucket <name>` to verify.
   - **Output:** ROOT_CAUSE_FOUND, layer = presigned URL region
     mismatch.

3. **Presigned for a different identity than intended.**
   - A presigned URL is bound to the signing principal's permissions at
     the time of signing. If the signer's permissions change (revoked,
     role deleted, policy tightened), the URL fails.
   - The signing principal's identity policy still applies — a presigned
     URL does NOT bypass IAM. Verify the signer has the action at
     signing time AND at request time.
   - **Output:** ROOT_CAUSE_FOUND, layer = presigned URL signer
     permission revoked.

4. **Bucket policy denies the calling principal.**
   - A presigned URL authenticates the request as the SIGNER, not as an
     anonymous principal. If the bucket policy explicitly denies the
     signer's ARN, the URL fails.
   - Read the bucket policy Deny statements.

5. **BPA blocking public presigned URL.**
   - A presigned URL is not "public" in the BPA sense — it is
     authenticated as the signer. BPA does NOT block presigned URLs
     unless `RestrictPublicBuckets` is True AND the bucket has a public
     policy. (Rare.)
   - However, if the bucket policy has `Principal: "*"` AND BPA is on,
     the policy is restricted to in-account principals only — a
     presigned URL signed by an out-of-account principal fails.

6. **Signature version mismatch.**
   - S3 presigned URLs use SigV4 (SigV2 is deprecated and rejected in
     modern regions). Verify the URL contains `X-Amz-Signature`
     (hex string), `X-Amz-SignedHeaders`, `X-Amz-Algorithm=AWS4-HMAC-SHA256`.
   - **Output:** ROOT_CAUSE_FOUND, layer = signature version mismatch.


## Step 6: Unexpected public access diagnostic path

### Step 6: Unexpected public access diagnostic path

Use when a bucket "should be private" but is publicly readable.

1. **Account-level BPA not enabled.**
   - The single most effective public-access block. If account-level BPA
     is off, bucket-level public access is allowed by any permissive
     bucket policy or ACL.
   - `aws s3control get-public-access-block --account-id <acct>`.
   - **Output:** ROOT_CAUSE_FOUND, layer = account-level BPA disabled.
     Recommend enable at account level (covers all current + future
     buckets).

2. **Bucket-level BPA not enabled (and account-level is also off).**
   - If account-level is off and bucket-level is off, the bucket inherits
     no BPA protection. Both scopes must be checked.

3. **Legacy ACL `AllUsers` / `AuthenticatedUsers`.**
   - `aws s3api get-bucket-acl --bucket <name>` and
     `aws s3api get-object-acl --bucket <name> --key <key>`.
   - `AllUsers` = `http://acs.amazonaws.com/groups/global/AllUsers`
     (anyone on the internet).
   - `AuthenticatedUsers` = anyone with an AWS account (free-tier
     signable — effectively public).
   - If Object Ownership is `BucketOwnerEnforced`, ACLs are disabled and
     any grant in the ACL output is a stale no-op.

4. **Public bucket policy (`Principal: "*"`).**
   - Read bucket policy. A statement with `Effect: Allow`,
     `Principal: "*"`, `Action: s3:GetObject` (or any read/write action),
     `Resource: arn:aws:s3:::bucket/*`, and no restrictive `Condition`
     is a public read path.
   - **Output:** ROOT_CAUSE_FOUND, layer = bucket policy wildcard Allow.

5. **Access Point policy with `Principal: "*"`.**
   - Each Access Point has its own policy. A restrictive bucket policy
     does NOT prevent access through a permissive Access Point.
   - Enumerate APs: `aws s3control list-access-points --account-id <acct>`
     (per region). For each AP, fetch its policy and audit.
   - **Output:** ROOT_CAUSE_FOUND, layer = Access Point policy wildcard
     Allow.

6. **MRAP (Multi-Region Access Point) propagating public access.**
   - A MRAP has a single global ARN. A public MRAP policy exposes all
     underlying regional buckets. Audit via
     `aws s3control get-multi-region-access-point-policy`.

7. **S3 website hosting amplifying exposure.**
   - A bucket configured for static website hosting requires public
     read. If the bucket is also website-enabled, it is indexed by
     search engines and discoverable via the
     `s3-website-<region>.amazonaws.com` endpoint.


## Diagnostic command reference (13 ordered commands)

```bash
# 1. Confirm the caller identity. Reveals assumed-role vs federated.
aws sts get-caller-identity --profile <profile>

# 2. Pull the CloudTrail event. errorMessage disambiguates implicit vs
#    explicit deny.
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=GetObject \
  --start-time $(date -d '-1 hour' +%s) \
  --end-time $(date +%s) \
  --profile <profile>

# 3. Read the bucket policy. Look for Allow matching the caller's ARN
#    AND Deny statements with matching conditions.
aws s3api get-bucket-policy --bucket <name> --profile <profile>

# 4. Read the bucket's BPA (both scopes).
aws s3control get-public-access-block --account-id <acct> --profile <profile>
aws s3api get-public-access-block --bucket <name> --profile <profile>

# 5. Read the bucket's Object Ownership setting.
aws s3api get-bucket-ownership-controls --bucket <name> --profile <profile>

# 6. Read the bucket ACL and the object ACL.
aws s3api get-bucket-acl --bucket <name> --profile <profile>
aws s3api get-object-acl --bucket <name> --key <key> --profile <profile>

# 7. Read the bucket's encryption configuration to identify the KMS key.
aws s3api get-bucket-encryption --bucket <name> --profile <profile>

# 8. For SSE-KMS buckets, read the key policy and check for the caller.
aws kms describe-key --key-id <key-id> --profile <profile>
aws kms get-key-policy --key-id <key-id> --policy-name default --profile <profile>

# 9. Simulate the caller's identity policy.
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::<acct>:role/<role> \
  --action-names s3:GetObject kms:Decrypt \
  --resource-arns arn:aws:s3:::bucket/key arn:aws:kms:<region>:<acct>:key/<id> \
  --output json --profile <profile>

# 10. Check Object Lock retention on the specific key (PutObject /
     DeleteObject issues only).
aws s3api get-object-retention --bucket <name> --key <key> --profile <profile>
aws s3api get-object-legal-hold --bucket <name> --key <key> --profile <profile>

# 11. Enumerate S3 Access Points and read their policies.
for r in us-east-1 us-west-2 eu-west-1 ap-southeast-2; do
  aws s3control list-access-points --account-id <acct> --region "$r" --profile <profile>
done
aws s3control get-access-point-policy --account-id <acct> --name <ap> --profile <profile>

# 12. For VPC-attached callers, inspect the VPC endpoint policy.
aws ec2 describe-vpc-endpoints --filters Name=vpc-id,Values=<vpc> --profile <profile>

# 13. For CloudFront origins, verify the OAC vs OAI principal in the
#    bucket policy.
#    CloudFront OAC principal:
#      Principal.Service: cloudfront.amazonaws.com
#      Condition.StringEquals.aws:SourceArn: arn:aws:cloudfront::<acct>:distribution/<id>
```
