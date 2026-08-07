# Bucket Policy Examples — S3 Secure Bucket Deployer

Reference policy templates for HTTPS-only enforcement, SSE-KMS / SSE-S3
upload enforcement, and log-delivery grants. Substitute `<BUCKET>`,
`<ACCOUNT>`, `<REGION>`, and `<KEY-ID>` as needed. Stored here so the
main skill body stays scannable; see Step 5 of the provisioning
procedure for when to apply each variant.

## Combined HTTPS-only + SSE enforcement (canonical, referenced from Step 5)

This is the default policy for production buckets. It enforces two
invariants together so that one misconfigured client cannot weaken
either:

1. **HTTPS-only** (`DenyInsecureTransport`): denies any `s3:*` API
   call where `aws:SecureTransport` is `false` (plain HTTP). The
   `Resource` list must include BOTH the bucket ARN (for object-level
   actions like `s3:ListBucket`) and the object ARN with `/*` (for
   object-level actions like `s3:GetObject` / `s3:PutObject`).
2. **SSE enforcement** (`DenyUnEncryptedObjectUploads`): denies
   `s3:PutObject` unless the client sets the
   `s3:x-amz-server-side-encryption` header to an allowed value. The
   `StringNotEquals` condition means "deny if the header is NOT one
   of these values."

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyInsecureTransport",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::<BUCKET>",
        "arn:aws:s3:::<BUCKET>/*"
      ],
      "Condition": {
        "Bool": { "aws:SecureTransport": "false" }
      }
    },
    {
      "Sid": "DenyUnEncryptedObjectUploads",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::<BUCKET>/*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": ["AES256", "aws:kms"]
        }
      }
    }
  ]
}
```

Apply with:

```bash
aws s3api put-bucket-policy --bucket <BUCKET> --policy file://policy.json
```

### Variants of the SSE condition

| Bucket encryption mode | Allowed header values | Why |
|---|---|---|
| SSE-S3 default | `["AES256", "aws:kms"]` | accept either; lets clients pick |
| SSE-KMS required | `["aws:kms"]` | reject SSE-S3 uploads; forces KMS |
| SSE-KMS with specific key | add `s3:x-amz-server-side-encryption-aws-kms-key-id: <KEY-ARN>` | pin uploads to one CMK |

## SSE-S3 variant (HTTPS-only, no SSE enforcement)

For buckets where encryption is the default and you do not need to
force the header on every upload (e.g., internal dev buckets):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyInsecureTransport",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::<BUCKET>",
        "arn:aws:s3:::<BUCKET>/*"
      ],
      "Condition": {
        "Bool": { "aws:SecureTransport": "false" }
      }
    }
  ]
}
```

## Log-delivery grant (apply to the LOG TARGET bucket)

S3 server access logs are delivered by the `logging.s3.amazonaws.com`
service principal. When the log target uses
`ObjectOwnership=BucketOwnerEnforced` (recommended), ACLs are disabled
and the legacy `log-delivery` ACL grant stops working — you MUST use a
bucket policy grant instead.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowS3LogDelivery",
      "Effect": "Allow",
      "Principal": { "Service": "logging.s3.amazonaws.com" },
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::<LOG-BUCKET>/*"
    }
  ]
}
```

If logs need to flow from buckets in OTHER accounts, also include
their account IDs:

```json
{
  "Condition": {
    "StringEquals": {
      "aws:SourceAccount": ["111122223333", "444455556666"]
    }
  }
}
```

## Cross-account read access ( BucketOwnerEnforced-safe )

When the bucket has `BucketOwnerEnforced`, cross-account access MUST
flow through the bucket policy — ACLs are disabled. Minimum-viable
cross-account read grant:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCrossAccountRead",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::<DEST-ACCOUNT>:root" },
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::<BUCKET>",
        "arn:aws:s3:::<BUCKET>/*"
      ]
    }
  ]
}
```

For SSE-KMS buckets, the cross-account principal ALSO needs
`kms:Decrypt` on the KMS key policy — the bucket policy alone is not
enough. This is the second access gate that makes SSE-KMS valuable.

## Why `Principal: "*"` is safe here

All four templates above use `Principal: "*"` for the DENY
statements. This is safe because:

1. The `Deny` blocks ALL principals (including the bucket owner)
   unless the condition is met. The condition is "use HTTPS" or
   "set the SSE header" — both are client-side requirements, not
   identity requirements.
2. BPA at the account level prevents anyone from attaching a MORE
   PERMISSIVE policy later. The deny statements here set the floor.

Do NOT use `Principal: "*"` with `Effect: "Allow"` unless you intend
public access — BPA will block that attach anyway, but the intent is
suspicious and will fail security review.
