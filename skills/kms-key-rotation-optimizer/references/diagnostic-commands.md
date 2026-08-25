# Diagnostic Commands — KMS Key Rotation Optimizer

Pre-flight data sources and audit procedures moved verbatim from SKILL.md.

## Pre-flight data sources (moved from SKILL.md)

1. Key inventory: `aws kms list-keys` + `aws kms describe-key` per key
2. Rotation status: `aws kms get-key-rotation-status`
3. Alias inventory: `aws kms list-aliases`
4. Grant inventory: `aws kms list-grants --key-id <id>`
5. Resource tags: `aws kms list-resource-tags --key-id <id>`
6. API call volume (14-30 day): `aws cloudtrail lookup-events` (Decrypt, Encrypt, GenerateDataKey)
7. Cost Explorer breakdown: `aws ce get-cost-and-usage --filter "Service=KeyManagementService"`

### Step 1 — Unused key detection procedure (moved from SKILL.md)

```
For each customer-managed key:
  1. CloudTrail lookup-events for Decrypt, Encrypt, GenerateDataKey (30 days)
  2. If total events == 0 → candidate for deletion
  3. Cross-check resource associations:
     - S3 bucket default encryption configs
     - EBS volume encryption
     - RDS encryption at rest
     - Secrets Manager
     - Lambda environment encryption
  4. If no resource associations AND 0 API calls → schedule deletion
```

### Step 1 — Key consolidation procedure (moved from SKILL.md)

```
For keys serving the same application or environment:
  1. Identify keys with < 100 API calls/month
  2. Check if key policies are identical or overlapping
  3. If two keys serve the same app with the same access pattern:
     → Consolidate into a single key (update resource configs)
     → Re-encrypt data under the surviving key (optional)
     → Schedule deletion of the redundant key
     → Saving: $1/month per eliminated key
```

### Step 3 — Grant audit procedure (moved from SKILL.md)

```
For each key with grants:
  1. aws kms list-grants --key-id <id>
  2. For each grant:
     - Check ExpiryDate (if past → retire)
     - Check GranteePrincipal (if deleted IAM role → retire)
     - Check last CloudTrail usage (if no Decrypt/Encrypt under the
       grant in 30 days → candidate for retirement)
  3. Retire expired grants:
     aws kms retire-grant --key-id <id> --grant-id <grant-id>
```

### Step 4 — Alias audit procedure (moved from SKILL.md)

```
For each key referenced by applications:
  1. Check if the key has an alias (aws kms list-aliases --key-id <id>)
  2. If no alias → create one:
     aws kms create-alias --alias-name alias/<app-name> --target-key-id <id>
  3. Audit application code for hardcoded key ARNs or IDs
  4. Recommend alias-based references everywhere
```

### Step 5 — Cross-account audit procedure (moved from SKILL.md)

```
For each customer-managed key:
  1. Check key policy for cross-account principals
  2. If cross-account access exists:
     - Verify grants are active and not expired
     - Verify the consuming account actually uses the key
     - If the consuming account has its own duplicate key:
       → Consolidate (use one key cross-account OR let each account
         use its own AWS-managed key)
```

### Step 6 — Multi-region audit procedure (moved from SKILL.md)

```
For each multi-region key:
  1. List all replicas (describe-key, filter MultiRegion=true)
  2. For each replica:
     - CloudTrail lookup-events in the replica's region (30 days)
     - If 0 API calls → delete the replica
  3. If replicas exist only for DR but DR has never been tested:
     - Evaluate whether the replica is justified by compliance
     - If not, delete the replica and recreate during DR drill
```

### Step 6 — Multi-region cost math (moved from SKILL.md)

```
Primary key:       $1/month
Each replica:      $1/month per region
API calls:         $0.03 per 10K per region (billed in-region)

A 5-region multi-region key with no DR traffic costs $6/month.
If only us-east-1 and eu-west-1 have real traffic:
  → Delete replicas in the 3 unused regions
  → Saving: $3/month ($36/year)
```

### Step 7 — PendingDeletion audit procedure (moved from SKILL.md)

```
For keys in PendingDeletion state:
  1. Check remaining days until deletion
  2. If billing continues (it does until permanent deletion):
     → No optimization possible; wait for window to expire
  3. If the key was scheduled by mistake:
     → Cancel deletion: aws kms cancel-key-deletion --key-id <id>
```
