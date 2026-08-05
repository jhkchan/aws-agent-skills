# End-to-end usage scenario: glue-crawler-job-auditor

A walkthrough showing the skill auditing a Glue job that has both a
NO_ENCRYPTION finding (catalog EncryptionAtRest DISABLED) and an
OVERPERMISSIVE_ROLE finding (s3:* on *), demonstrating severity aggregation,
the catalog-vs-source encryption distinction, and the pass-role awareness
for `glue:CreateJob`.

## Input (user prompt)

> Review this Glue job before we promote it to production. It reads from an
> S3 source and writes to the Glue Data Catalog.

Resource: job nightly-etl-pipeline
GlueVersion: 3.0
Role: arn:aws:iam::111111111111:role/glue-etl-nightly
SecurityConfiguration: prod-glue-sec

DataCatalogEncryptionSettings:
  EncryptionAtRest:
    EncryptionMode: DISABLED
  ConnectionPasswordEncryption:
    ReturnConnectionPasswordEncrypted: true
    AwsKmsKeyId: alias/glue-catalog

SecurityConfiguration (prod-glue-sec):
  EncryptionConfiguration:
    CloudWatchEncryption: {CloudWatchEncryptionMode: SSE-KMS}
    S3Encryptions: [{EncryptionMode: SSE-KMS}]
    JobBookmarksEncryption: {JobBookmarksEncryptionMode: CSE-KMS}

S3 source bucket (etl-source-nightly):
  server-side-encryption-configuration:
    Rules:
      - ApplyServerSideEncryptionByDefault: {SSEAlgorithm: AES256}

Execution role policy (glue-etl-nightly):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3Access",
      "Effect": "Allow",
      "Action": "s3:*",
      "Resource": "*"
    },
    {
      "Sid": "GlueAndCreate",
      "Effect": "Allow",
      "Action": ["glue:*", "iam:PassRole"],
      "Resource": "*"
    }
  ]
}
```

## Expected output (with skill loaded)

```text
RESOURCE: nightly-etl-pipeline
VERDICT: NO_ENCRYPTION
REASON: DataCatalogEncryptionSettings.EncryptionAtRest.EncryptionMode is
DISABLED (Step 1) — catalog metadata including column names is stored in
plaintext. The execution role also grants s3:* and glue:* on * plus
iam:PassRole on * (Step 3) — a pass-role escalation vector via
glue:CreateJob.
FINDINGS:
  - [NO_ENCRYPTION] EncryptionAtRest.EncryptionMode is DISABLED — catalog metadata is plaintext (Step 1)
  - [OVERPERMISSIVE_ROLE] Role grants s3:* on Resource "*" (Step 3)
  - [OVERPERMISSIVE_ROLE] Role grants glue:* on Resource "*" and iam:PassRole on "*" — glue:CreateJob is a pass-role vector (Step 3 / Step 0)
  - [OK] S3 source bucket has SSE-S3 enabled (Step 2)
  - [OK] SecurityConfiguration present with SSE-KMS logs, SSE-KMS spills, CSE-KMS bookmarks (Step 4b/4c)
  - [OK] GlueVersion 3.0 is supported — not EOL (Step 4d)
REMEDIATION:
  1. Enable catalog encryption (BREAKING — verify catalog readers have kms:Decrypt first):
     aws glue put-data-catalog-encryption-settings \
       --region us-east-1 \
       --data-catalog-encryption-settings \
         EncryptionAtRest={EncryptionMode=SSE-KMS,SseAwsKmsKeyId=alias/glue-catalog},\
         ConnectionPasswordEncryption={ReturnConnectionPasswordEncrypted=true,AwsKmsKeyId=alias/glue-catalog}
  2. Scope the role: replace s3:* with s3:GetObject/s3:ListBucket on the specific source bucket ARN;
     replace glue:* with named actions (BatchCreatePartition, GetTable, GetDatabase) on the catalog ARN;
     restrict iam:PassRole to the specific Glue service-role ARN and add iam:PassedToService: glue.amazonaws.com.
  3. Verify: re-audit after changes; confirm the job still runs (bookmark read needs kms:Decrypt on the bookmark key).
```

## Why the baseline (no-skill) response misses this

A generic assistant typically notes that "encryption is disabled" and "the
role is broad" but does NOT:

- Distinguish catalog metadata encryption (EncryptionAtRest) from source
  data encryption (bucket SSE) — treating "the job has a SecurityConfiguration"
  as sufficient when the catalog itself is plaintext.
- Flag `glue:*` + `iam:PassRole` as a pass-role escalation vector
  (`glue:CreateJob` is structurally identical to the `iam:PassRole` +
  EC2/Lambda pattern).
- Warn that enabling catalog encryption is a BREAKING change for downstream
  readers without `kms:Decrypt` on the catalog key.
- Produce a deterministic VERDICT with enumerated FINDINGS and per-finding
  step citations.
