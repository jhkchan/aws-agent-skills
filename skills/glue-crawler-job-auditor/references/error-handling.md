# Error Handling and Remediation — Glue Crawler & Job Auditor

Per-verdict remediation guidance moved verbatim from SKILL.md (progressive disclosure — load on demand).

## Remediation guidance (per verdict)

### For NO_ENCRYPTION — catalog EncryptionAtRest DISABLED (Step 1)

1. **Before enabling**, enumerate catalog readers and verify each has
   `kms:Decrypt` on the catalog key (or grant it). This is a breaking change.
2. Enable catalog encryption:
   ```bash
   aws glue put-data-catalog-encryption-settings \
     --region <r> \
     --data-catalog-encryption-settings \
       EncryptionAtRest={EncryptionMode=SSE-KMS,SseAwsKmsKeyId=alias/glue-catalog},\
       ConnectionPasswordEncryption={ReturnConnectionPasswordEncrypted=true,AwsKmsKeyId=alias/glue-catalog}
   ```
3. Verify: `aws glue get-data-catalog-encryption-settings --region <r>`.
4. If using a customer-managed CMK, ensure the key policy grants
   `kms:Decrypt` to every catalog reader principal.

### For NO_ENCRYPTION — S3 source unencrypted (Step 2)

1. Enable SSE on the source bucket:
   ```bash
   aws s3api put-bucket-encryption \
     --bucket <source-bucket> \
     --server-side-encryption-configuration \
       '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
   ```
2. For SSE-KMS, add the KMS key ARN and ensure the execution role has
   `kms:Decrypt` on the key.
3. Existing objects are NOT retroactively encrypted by bucket-default
   changes. Use S3 Batch Operations or a Copy job to encrypt existing data.

### For OVERPERMISSIVE_ROLE (Step 3)

1. Derive a least-privilege policy from CloudTrail `glue:*` and `s3:*`
   events for the role over the last 90 days.
2. Replace `glue:*` with named actions (`glue:BatchCreatePartition`,
   `glue:GetTable`, `glue:GetDatabase`, `glue:UpdateTable`, etc.) scoped to
   the specific catalog / database / table ARNs.
3. Replace `s3:*` on `*` with `s3:GetObject` / `s3:ListBucket` on the
   specific source bucket ARN(s) and `s3:PutObject` on the spill / output
   bucket ARN(s).
4. Restrict `iam:PassRole` to the specific Glue service-role ARN the
   workload needs, and add `iam:PassedToService: glue.amazonaws.com` as a
   condition.
5. Convert `NotAction` / `NotResource` to explicit `Action` / `Resource`
   allow-lists.

### For CONFIG_GAP — JDBC SSL (Step 4a)

1. Update the connection to enforce SSL:
   ```bash
   aws glue update-connection \
     --connection-name <conn> \
     --connection-input '{
       "ConnectionType":"JDBC",
       "ConnectionProperties":{"JDBC_CONNECTION_URL":"...","JDBC_ENFORCE_SSL":"true","USERNAME":"..."},
       "PhysicalConnectionRequirements":{...}
     }'
   ```
2. For self-signed / private-CA databases, add `JDBC_CUSTOM_CERT` /
   `JDBC_CUSTOM_CERT_CHAIN` pointing to the uploaded CA cert in S3.

### For CONFIG_GAP — SecurityConfiguration missing (Step 4b)

1. Create a SecurityConfiguration:
   ```bash
   aws glue create-security-configuration \
     --name prod-glue-sec \
     --encryption-configuration '{
       "CloudWatchEncryption":{"CloudWatchEncryptionMode":"SSE-KMS"},
       "S3Encryptions":[{"EncryptionMode":"SSE-KMS"}],
       "JobBookmarksEncryption":{"JobBookmarksEncryptionMode":"CSE-KMS"}
     }'
   ```
2. Attach it to the job:
   ```bash
   aws glue update-job --job-name <name> --job-update '{"SecurityConfiguration":"prod-glue-sec"}'
   ```
3. For crawlers, set `CrawlerSecurityConfiguration` via `update-crawler`.

### For CONFIG_GAP — EOL Glue version (Step 4d)

1. Upgrade the job to Glue 4.0:
   ```bash
   aws glue update-job --job-name <name> \
     --job-update '{"GlueVersion":"4.0","Command":{"Name":"glueetl","ScriptLocation":"...","PythonVersion":"3"}}'
   ```
2. Test the job — Spark version changes (2.4 → 3.3) may require script
   adjustments (DataFrame API, partitioning behavior).

### For CONFIG_GAP — Connection password encryption disabled (Step 4e)

1. Enable it as part of the catalog encryption settings (see Step 1
   remediation — `ConnectionPasswordEncryption` is set in the same
   `PutDataCatalogEncryptionSettings` call as `EncryptionAtRest`).
2. Existing connections' passwords are re-encrypted on next read; no
   migration action is required for the passwords themselves.

### For OK

1. No remediation required for the current posture.
2. Recommend periodic re-audit — SecurityConfigurations can be deleted,
   catalog encryption can be disabled by a later change, and the role
   policy can drift.
3. For multi-region pipelines, verify the same posture in every region:
   ```bash
   for r in us-east-1 eu-west-1 ap-southeast-1; do
     echo "=== $r ==="
     aws glue get-data-catalog-encryption-settings --region $r
   done
   ```
   A us-east-1 SSE-KMS setting does NOT propagate — each region's catalog
   encryption is independent.

