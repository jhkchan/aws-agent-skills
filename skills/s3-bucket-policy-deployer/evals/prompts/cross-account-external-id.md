# Eval: cross-account-external-id

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — partner role ARN principal, shared/ prefix, aws:ExternalId condition, HTTPS-only Deny present

## Prompt

Grant partner account 998877665544 read access (GetObject +
ListBucket) to the "shared/" prefix on bucket
"prod-shared-data" in us-east-1 (account 123456789012).
Use ExternalId "partner-ext-abc123" to prevent the confused-
deputy problem. HTTPS-only Deny should also be present.
Bucket exists, ACLs disabled, BPA enabled.
