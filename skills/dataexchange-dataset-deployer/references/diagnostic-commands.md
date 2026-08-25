# Diagnostic Commands (load on demand) — Data Exchange Dataset Deployer

Subscription creation, revision/asset listing, and other per-step CLI
listings moved verbatim from SKILL.md. Loaded on demand.

---

## Step 1 — subscription creation and details commands (moved from SKILL.md)



**Create a subscription (subscribe to a product):**

```bash
# List available data sets
aws dataexchange list-data-sets \
  --region us-east-1

# Create a subscription (from AWS marketplace product)
aws marketplace subscribe \
  --product-id <product-id> \
  --region us-east-1
```

**View subscription details:**

```bash
# List revisions for a subscribed data set
aws dataexchange list-data-set-revisions \
  --data-set-id <data-set-id> \
  --region us-east-1

# Get revision details
aws dataexchange get-revision \
  --data-set-id <data-set-id> \
  --revision-id <revision-id> \
  --region us-east-1
```



## Step 2 — listing revisions and assets commands (moved from SKILL.md)



**List assets in a revision:**

```bash
aws dataexchange list-data-set-revisions \
  --data-set-id <data-set-id> \
  --region us-east-1

# Get assets for a specific revision
aws dataexchange get-revision \
  --data-set-id <data-set-id> \
  --revision-id <revision-id> \
  --region us-east-1
```


