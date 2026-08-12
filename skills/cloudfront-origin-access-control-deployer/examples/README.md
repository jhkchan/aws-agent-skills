# End-to-End Example: CloudFront OAC Deployment

A walkthrough showing how to use the
`cloudfront-origin-access-control-deployer` skill from invocation
through verification. Mirrors the structured-eval pattern of shipping
a concrete worked example per skill.

---

## Scenario

You are provisioning a CloudFront Origin Access Control for a
private S3 bucket encrypted with SSE-KMS. The distribution needs:

- S3 bucket: my-secure-bucket (us-east-1)
- CloudFront distribution: EDFDVBD6EXAMPLE
- Account: 111122223333
- SSE-KMS key: arn:aws:kms:us-east-1:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab
- Signing behavior: always-sign (sigv4 — required for SSE-KMS)
- Bucket is NOT configured for website hosting

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-cloudfront-oac
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a CloudFront OAC for distribution EDFDVBD6EXAMPLE
      serving S3 bucket my-secure-bucket. The bucket is
      SSE-KMS encrypted. Account 111122223333."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a cloudfront oac"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
CLOUDFRONT_OAC: EDFDVBD6EXAMPLE → my-secure-bucket (E2QWRUOACID123)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] S3 bucket: my-secure-bucket (region: us-east-1)
  [✓] Origin type: S3 (not Website Endpoint)
  [✓] OAC created: E2QWRUOACID123 (SigningBehavior: always-sign)
  [✓] Distribution origin: EDFDVBD6EXAMPLE → OriginAccessControlId=E2QWRUOACID123
  [✓] S3 bucket policy: cloudfront.amazonaws.com s3:GetObject with AWS:SourceArn=arn:aws:cloudfront::111122223333:distribution/EDFDVBD6EXAMPLE
  [✓] SSE-KMS: enabled (KMS key policy grants cloudfront.amazonaws.com kms:Decrypt)
  [✓] Multi-distribution: single distribution
  [✓] Bucket public access: blocked (OAC only)
  [✓] Tags: Environment=production, Encryption=sse-kms
VERIFICATION_COMMANDS:
  aws cloudfront get-origin-access-control --id E2QWRUOACID123
  aws cloudfront get-distribution-config --id EDFDVBD6EXAMPLE
  aws s3api get-bucket-policy --bucket my-secure-bucket
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the OAC (always-sign required for SSE-KMS)
OAC_ID=$(aws cloudfront create-origin-access-control \
  --origin-access-control-config \
    '{"Name":"oac-my-secure-bucket","Description":"OAC for SSE-KMS bucket","SigningProtocol":"sigv4","SigningBehavior":"always-sign","OriginAccessControlOriginType":"s3"}' \
  --query 'OriginAccessControl.Id' --output text)

echo "OAC ID: $OAC_ID"

# Step 2: Update the S3 bucket policy
aws s3api put-bucket-policy --bucket my-secure-bucket --policy '{
  "Version": "2012-10-17",
  "Statement": {
    "Sid": "AllowCloudFrontServicePrincipalReadOnly",
    "Effect": "Allow",
    "Principal": {"Service": "cloudfront.amazonaws.com"},
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::my-secure-bucket/*",
    "Condition": {
      "StringEquals": {
        "AWS:SourceArn": "arn:aws:cloudfront::111122223333:distribution/EDFDVBD6EXAMPLE"
      }
    }
  }
}'

# Step 3: Update the KMS key policy (REQUIRED for SSE-KMS)
aws kms put-key-policy \
  --key-id arn:aws:kms:us-east-1:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab \
  --policy-name default \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Sid": "AllowCloudFrontServicePrincipalKMSDecrypt",
      "Effect": "Allow",
      "Principal": {"Service": "cloudfront.amazonaws.com"},
      "Action": "kms:Decrypt",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "AWS:SourceArn": "arn:aws:cloudfront::111122223333:distribution/EDFDVBD6EXAMPLE"
        }
      }
    }]
  }'

# Step 4: Update the distribution origin to reference the OAC
ETAG=$(aws cloudfront get-distribution-config \
  --id EDFDVBD6EXAMPLE --query 'ETag' --output text)
# Set Origins.Items[0].OriginAccessControlId = $OAC_ID in the config JSON
aws cloudfront update-distribution \
  --id EDFDVBD6EXAMPLE \
  --if-match "$ETAG" \
  --distribution-config file://updated-distribution-config.json
```

---

## Step 4 — Post-deployment verification

```bash
# Verify the OAC exists and uses always-sign
aws cloudfront get-origin-access-control --id "$OAC_ID" \
  --query 'OriginAccessControl.OriginAccessControlConfig.SigningBehavior'

# Verify the distribution references the OAC
aws cloudfront get-distribution-config --id EDFDVBD6EXAMPLE \
  --query 'DistributionConfig.Origins.Items[0].OriginAccessControlId'

# Verify the bucket policy grants cloudfront.amazonaws.com
aws s3api get-bucket-policy --bucket my-secure-bucket \
  --output text --query Policy | jq '.Statement[].Principal.Service'

# Verify the KMS key policy grants cloudfront.amazonaws.com kms:Decrypt
aws kms get-key-policy \
  --key-id 1234abcd-12ab-34cd-56ef-1234567890ab \
  --policy-name default \
  --output text --query Policy | jq '.Statement[] | select(.Principal.Service=="cloudfront.amazonaws.com") | .Action'
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Bucket policy | Creates OAC only | OAC + bucket policy with cloudfront.amazonaws.com + AWS:SourceArn | Without the bucket policy, CloudFront gets 403 from S3 |
| Signing behavior | Default or unspecified | always-sign for SSE-KMS | SSE-KMS requires sigv4-signed requests for KMS decryption |
| KMS key policy | Not updated | Grants cloudfront.amazonaws.com kms:Decrypt | Both S3 and KMS policies must allow CloudFront |
| Origin type | Not checked | Verifies no website hosting | OAC does not work with Website Endpoint |
| OAC principal | Tries OAC ID | Uses cloudfront.amazonaws.com service principal | S3 policies don't understand OAC IDs |
| Multi-distribution | Single SourceArn | Lists all distribution ARNs | Missing ARNs cause 403 for unlisted distributions |

---

## Related artifacts

- **Skill definition:** `skills/cloudfront-origin-access-control-deployer/SKILL.md`
- **OAC and bucket policy guide:** `skills/cloudfront-origin-access-control-deployer/references/oac-and-bucket-policy.md`
- **Migration and SSE-KMS guide:** `skills/cloudfront-origin-access-control-deployer/references/oai-migration-and-sse-kms.md`
- **Eval suite:** `skills/cloudfront-origin-access-control-deployer/evals/evals.json`
- **Legacy test cases:** `skills/cloudfront-origin-access-control-deployer/eval/test-cases.yaml`
