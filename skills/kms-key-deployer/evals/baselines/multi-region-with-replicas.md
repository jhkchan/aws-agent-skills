# Baseline (no-skill) — multi-region-with-replicas

> This is the response a model produces **without** the skill definition.
> It creates the multi-Region key and replicates, but misses that
> multi-Region keys cannot auto-rotate (often running enable-key-rotation
> which fails silently), and forgets that replica policies are
> independent from the primary.

---

```bash
# Create primary
PRIMARY=$(aws kms create-key \
  --description "DR CMK primary" \
  --multi-region \
  --query 'KeyMetadata.KeyId' --output text)

# Replicate
aws kms replicate-key \
  --key-id $PRIMARY \
  --replica-region us-west-2

aws kms replicate-key \
  --key-id $PRIMARY \
  --replica-region eu-west-1

aws kms create-alias --alias-name alias/dr-cmk --target-key-id $PRIMARY
aws kms enable-key-rotation --key-id $PRIMARY
```

The replicas should automatically inherit the primary's policy.
