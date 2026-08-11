# End-to-End Example: CloudFront KeyValueStore Deployment

A walkthrough showing how to use the `cloudfront-keyvaluestore-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a CloudFront KeyValueStore for A/B testing
traffic routing. The deployment needs:

- KVS store: `ab-testing-kvs`
- Use case: A/B testing (percentage-based traffic split)
- CloudFront Function: `ab-test-router` (reads KVS at the edge)
- Function runtime: `cloudfront-js-2.0` (required for KVS API)
- Distribution: `E1234567890ABC` (viewer-request event)
- Key schema: kebab-case with `ab-` prefix

Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-cloudfront-keyvaluestore
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a CloudFront KeyValueStore named ab-testing-kvs for
      A/B testing. I need a CloudFront Function named ab-test-router
      that reads the KVS to route traffic. Distribution E1234567890ABC.
      Account: 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create cloudfront keyvaluestore"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
KVS_DEPLOYMENT: ab-testing-kvs (arn:aws:cloudfront::123456789012:key-value-store/abc-123)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] KVS store: ab-testing-kvs — created
  [✓] Store size: ~200 bytes / 1 MB (0.02% used)
  [✓] Key count: 4 keys
  [✓] Key schema: kebab-case with ab- prefix
  [✓] Use case: A/B testing
  [✓] Function name: ab-test-router
  [✓] Function runtime: cloudfront-js-2.0 (REQUIRED for KVS)
  [✓] Function stage: LIVE (published)
  [✓] KVS-function link: associated via --key-value-store-associations
  [✓] Distribution: E1234567890ABC — viewer-request event
  [✓] Write path: CLI (put-key for traffic-split changes)
  [✓] etag handling: re-fetch before each write
  [✓] Propagation: eventual consistency acknowledged (seconds to minutes)
  [✓] Tags: Environment=production, UseCase=ab-testing
VERIFICATION_COMMANDS:
  aws cloudfront-keyvaluestore describe-key-value-store --kvs-arn arn:aws:cloudfront::123456789012:key-value-store/abc-123
  aws cloudfront-keyvaluestore list-keys --kvs-arn arn:aws:cloudfront::123456789012:key-value-store/abc-123
  aws cloudfront describe-function --name ab-test-router
  aws cloudfront get-distribution-config --id E1234567890ABC
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the KVS store
KVS_ARN=$(aws cloudfront create-key-value-store \
  --name "ab-testing-kvs" \
  --comment "A/B testing traffic split configuration" \
  --query 'KeyValueStore.ARN' --output text)

# Step 2: Populate key-value pairs (re-fetch etag before each write)
ETAG=$(aws cloudfront-keyvaluestore describe-key-value-store \
  --kvs-arn "$KVS_ARN" --query 'ETag' --output text)

aws cloudfront-keyvaluestore put-key \
  --kvs-arn "$KVS_ARN" \
  --key "ab-active" --value "true" --if-match "$ETAG"

ETAG=$(aws cloudfront-keyvaluestore describe-key-value-store \
  --kvs-arn "$KVS_ARN" --query 'ETag' --output text)

aws cloudfront-keyvaluestore put-key \
  --kvs-arn "$KVS_ARN" \
  --key "ab-percentage" --value "50" --if-match "$ETAG"

# Step 3: Create the CloudFront Function with KVS access
aws cloudfront create-function \
  --name "ab-test-router" \
  --function-config '{"Comment":"A/B test router via KVS","Runtime":"cloudfront-js-2.0"}' \
  --function-code fileb://function.js \
  --key-value-store-associations '["'"$KVS_ARN"'"]'

# Step 4: Publish the function (required for edge execution)
FUNCTION_ETAG=$(aws cloudfront describe-function \
  --name "ab-test-router" --query 'ETag' --output text)

aws cloudfront publish-function \
  --name "ab-test-router" \
  --if-match "$FUNCTION_ETAG"

# Step 5: Associate the function with the distribution
# (update distribution config with FunctionAssociations)
```

---

## Step 4 — Post-deployment verification

```bash
# KVS store — verify size, key count, status
aws cloudfront-keyvaluestore describe-key-value-store \
  --kvs-arn "$KVS_ARN"

# List all keys
aws cloudfront-keyvaluestore list-keys \
  --kvs-arn "$KVS_ARN"

# Function — verify runtime is cloudfront-js-2.0 and stage is LIVE
aws cloudfront describe-function \
  --name "ab-test-router" \
  --query 'FunctionSummary.{Runtime:FunctionConfig.Runtime,Stage:Stage}'

# Distribution — verify FunctionAssociations
aws cloudfront get-distribution-config \
  --id E1234567890ABC \
  --query 'DistributionConfig.DefaultCacheBehavior.FunctionAssociations'
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Function runtime | Default (js-1.0) | cloudfront-js-2.0 | KVS API only exists in 2.0 |
| KVS-function link | Links at distribution | Links at function | KVS is function-level, not distribution-level |
| etag handling | Ignores etag | Re-fetches before each write | Stale etag → PreconditionFailed |
| Read-write model | Assumes function can write | Read-only from function | Functions cannot write to KVS |
| Propagation | Assumes instant | Seconds to minutes | KVS is eventually consistent |
| Traffic split change | Redeploys function | Updates KVS via put-key | No code change needed |

---

## Related artifacts

- **Skill definition:** `skills/cloudfront-keyvaluestore-deployer/SKILL.md`
- **Functions KVS API detail:** `skills/cloudfront-keyvaluestore-deployer/references/kvs-functions-integration.md`
- **Provisioning CLI commands:** `skills/cloudfront-keyvaluestore-deployer/references/provisioning-cli-commands.md`
- **Slash command:** `commands/aws/deploy-cloudfront-keyvaluestore.md`
- **Eval suite:** `skills/cloudfront-keyvaluestore-deployer/evals/evals.json`
- **Legacy test cases:** `skills/cloudfront-keyvaluestore-deployer/eval/test-cases.yaml`
