# Error Handling — S3 Access Troubleshooter

Load-on-demand remediation procedures moved verbatim from SKILL.md.

## Remediation guidance

### For ARN-shape errors (GetObject on bucket ARN, ListBucket on object ARN)

1. Identify the action's required ARN shape:
   - Object-level actions → `arn:aws:s3:::bucket/*`
   - Bucket-level actions → `arn:aws:s3:::bucket`
2. Update the identity policy to include BOTH ARN shapes:
   ```json
   "Resource": [
     "arn:aws:s3:::bucket-name",
     "arn:aws:s3:::bucket-name/*"
   ]
   ```
3. Re-run `aws iam simulate-principal-policy` to confirm `allowed`.

### For KMS key policy cross-account denies

1. Identify the calling role ARN and the KMS key ARN.
2. Add a statement to the KEY policy granting `kms:Decrypt` (read) and/or
   `kms:GenerateDataKey` (write) to the caller's role ARN.
3. ALSO verify the caller's identity policy has the corresponding KMS
   action on the key ARN (cross-account intersection at KMS).
4. If the workflow uses grants, prefer `kms:CreateGrant` over editing the
   key policy for ephemeral access.

### For bucket policy missing cross-account principal

1. Add the caller's role ARN to the bucket policy's `Principal.AWS`:
   ```json
   {
     "Sid": "AllowCrossAccountRead",
     "Effect": "Allow",
     "Principal": { "AWS": "arn:aws:iam::<caller-acct>:role/<role>" },
     "Action": "s3:GetObject",
     "Resource": "arn:aws:s3:::bucket/*"
   }
   ```
2. Verify via simulator and via a real GetObject test.

### For BPA blocking intended public access

1. If the bucket is genuinely intended public (static website), the
   proper fix is CloudFront OAC in front of a private bucket — not
   disabling BPA. If a direct public bucket is required (rare, legacy),
   disable BPA at the bucket level (NOT account level) AND verify no
   SCP restricts BPA.
2. Account-level BPA should remain enabled in nearly all production
   accounts.

### For bucket policy SSE enforcement Deny

1. Update the PutObject request to include the required SSE header:
   ```
   aws s3api put-object --bucket <b> --key <k> --body <file> \
     --server-side-encryption aws:kms \
     --ssekms-key-id arn:aws:kms:<region>:<acct>:key/<id>
   ```

### For Object Lock retention / legal hold

1. `GOVERNANCE` mode: bypass with
   `s3:BypassGovernanceRetention` permission and a header
   `x-amz-bypass-governance-retention: TRUE` on the delete/overwrite.
2. `COMPLIANCE` mode: cannot be bypassed. Wait for the retain-until date
   or restore from a backup to a different key.

### For presigned URL failures

1. Re-sign with a fresh signing credential.
2. Verify the region matches the bucket via `aws s3api get-bucket-location`.
3. Verify the signer's identity policy allows the action at signing time.
4. Use short expirations (5-15 min) for interactive use; 7 days max for
   IAM-user-signed URLs.

### For CloudFront OAC migration

1. Update the bucket policy to use the OAC principal:
   ```json
   {
     "Sid": "AllowCloudFrontOAC",
     "Effect": "Allow",
     "Principal": { "Service": "cloudfront.amazonaws.com" },
     "Action": "s3:GetObject",
     "Resource": "arn:aws:s3:::bucket/*",
     "Condition": {
       "StringEquals": {
         "AWS:SourceArn": "arn:aws:cloudfront::<acct>:distribution/<dist-id>"
       }
     }
   }
   ```
2. Create the OAC in CloudFront console (replacing the legacy OAI).
3. Verify the CloudFront distribution can fetch objects.
