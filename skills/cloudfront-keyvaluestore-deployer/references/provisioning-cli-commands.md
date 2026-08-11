# Provisioning CLI Commands — CloudFront KeyValueStore Deployer

Full copy-pasteable CLI command sequence for provisioning CloudFront
KeyValueStore (KVS) with CloudFront Functions integration, A/B testing,
feature flags, and IP allowlists. Variables to substitute: `<kvs-name>`,
`<account-id>`, `<kvs-arn>`, `<function-name>`, `<distribution-id>`.

## Step 0: Prerequisites check

```bash
# Confirm caller identity
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"

# Confirm CloudFront distributions exist
aws cloudfront list-distributions --query 'DistributionList.Items[*].Id' --output table
```

## Step 1: Create the KVS store

```bash
KVS_ARN=$(aws cloudfront create-key-value-store \
  --name "ab-testing-kvs" \
  --comment "A/B testing traffic split configuration" \
  --query 'KeyValueStore.ARN' --output text)

echo "KVS ARN: $KVS_ARN"
```

## Step 2: Retrieve the KVS etag (required for all writes)

```bash
ETAG=$(aws cloudfront-keyvaluestore describe-key-value-store \
  --kvs-arn "$KVS_ARN" \
  --query 'ETag' --output text)

echo "Etag: $ETAG"
```

## Step 3: Populate key-value pairs

```bash
# Re-fetch etag before EACH write (etag changes on every mutation)

# Key 1: traffic-split
ETAG=$(aws cloudfront-keyvaluestore describe-key-value-store \
  --kvs-arn "$KVS_ARN" --query 'ETag' --output text)

aws cloudfront-keyvaluestore put-key \
  --kvs-arn "$KVS_ARN" \
  --key "traffic-split" \
  --value "variant-b" \
  --if-match "$ETAG"

# Key 2: ab-percentage
ETAG=$(aws cloudfront-keyvaluestore describe-key-value-store \
  --kvs-arn "$KVS_ARN" --query 'ETag' --output text)

aws cloudfront-keyvaluestore put-key \
  --kvs-arn "$KVS_ARN" \
  --key "ab-percentage" \
  --value "50" \
  --if-match "$ETAG"

# Key 3: ab-active
ETAG=$(aws cloudfront-keyvaluestore describe-key-value-store \
  --kvs-arn "$KVS_ARN" --query 'ETag' --output text)

aws cloudfront-keyvaluestore put-key \
  --kvs-arn "$KVS_ARN" \
  --key "ab-active" \
  --value "true" \
  --if-match "$ETAG"
```

## Step 4: List all keys

```bash
aws cloudfront-keyvaluestore list-keys \
  --kvs-arn "$KVS_ARN" \
  --output table
```

## Step 5: Create the CloudFront Function with KVS access

```bash
# function.js — reads KVS at the edge
cat > function.js << 'FUNCTION_EOF'
import cf from 'cloudfront';

const kvs = cf.openKvs();

function handler(event) {
    const request = event.request;
    if (kvs.get('ab-active') !== 'true') return request;

    const seed = request.headers['host'].value + request.querystring;
    const hash = Math.abs(
        seed.split('').reduce((h, c) => {
            h = ((h << 5) - h) + c.charCodeAt(0); return h | 0;
        }, 0)
    );
    const percentage = parseInt(kvs.get('ab-percentage') || '0', 10);
    if (hash % 100 < percentage) {
        request.headers['x-ab-variant'] = { value: 'variant-b' };
        request.uri = request.uri.replace('/api/', '/api-v2/');
    } else {
        request.headers['x-ab-variant'] = { value: 'variant-a' };
    }
    return request;
}
FUNCTION_EOF

FUNCTION_ETAG=$(aws cloudfront create-function \
  --name "ab-test-router" \
  --function-config '{"Comment":"A/B test router via KVS","Runtime":"cloudfront-js-2.0"}' \
  --function-code fileb://function.js \
  --key-value-store-associations '["'"$KVS_ARN"'"]' \
  --query 'ETag' --output text)

echo "Function ETag: $FUNCTION_ETAG"
```

## Step 6: Test the function (before publishing)

```bash
# Create a test event
cat > test-event.json << 'EVENT_EOF'
{
    "version": "1.0",
    "context": {
        "eventType": "viewer-request"
    },
    "viewer": {
        "ip": "192.168.1.1"
    },
    "request": {
        "method": "GET",
        "uri": "/api/data",
        "querystring": "param=value",
        "headers": {
            "host": { "value": "example.com" }
        }
    }
}
EVENT_EOF

aws cloudfront test-function \
  --name "ab-test-router" \
  --if-match "$FUNCTION_ETAG" \
  --event-object fileb://test-event.json \
  --query 'TestResult.FunctionOutput' --output text
```

## Step 7: Publish the function (required for edge execution)

```bash
FUNCTION_ETAG=$(aws cloudfront describe-function \
  --name "ab-test-router" --query 'ETag' --output text)

aws cloudfront publish-function \
  --name "ab-test-router" \
  --if-match "$FUNCTION_ETAG"
```

## Step 8: Associate the function with a distribution

```bash
DIST_ID="E1234567890ABC"

# Get current distribution config + ETag
DIST_CONFIG=$(aws cloudfront get-distribution-config \
  --id "$DIST_ID" --query 'DistributionConfig')

DIST_ETAG=$(aws cloudfront get-distribution-config \
  --id "$DIST_ID" --query 'ETag' --output text)

# Add FunctionAssociations to the DefaultCacheBehavior
echo "$DIST_CONFIG" | jq --arg fnarn "arn:aws:cloudfront::$ACCOUNT_ID:function/ab-test-router" '
  .DefaultCacheBehavior.FunctionAssociations = {
    "Quantity": 1,
    "Items": [{
      "FunctionARN": $fnarn,
      "EventType": "viewer-request"
    }]
  }
' > /tmp/updated-dist-config.json

aws cloudfront update-distribution \
  --id "$DIST_ID" \
  --if-match "$DIST_ETAG" \
  --distribution-config file:///tmp/updated-dist-config.json
```

## Step 9: Update KVS data (no function redeployment needed)

```bash
# Change traffic split to 100% variant-b
ETAG=$(aws cloudfront-keyvaluestore describe-key-value-store \
  --kvs-arn "$KVS_ARN" --query 'ETag' --output text)

aws cloudfront-keyvaluestore put-key \
  --kvs-arn "$KVS_ARN" \
  --key "ab-percentage" \
  --value "100" \
  --if-match "$ETAG"

# Change propagates to edge locations within seconds — no code redeployment
```

## Step 10: Delete a key

```bash
ETAG=$(aws cloudfront-keyvaluestore describe-key-value-store \
  --kvs-arn "$KVS_ARN" --query 'ETag' --output text)

aws cloudfront-keyvaluestore delete-key \
  --kvs-arn "$KVS_ARN" \
  --key "traffic-split" \
  --if-match "$ETAG"
```

## Verification

```bash
# KVS store details
aws cloudfront-keyvaluestore describe-key-value-store \
  --kvs-arn "$KVS_ARN"

# List all keys
aws cloudfront-keyvaluestore list-keys \
  --kvs-arn "$KVS_ARN"

# Get a specific key
aws cloudfront-keyvaluestore get-key \
  --kvs-arn "$KVS_ARN" \
  --key "ab-percentage"

# Function details (verify runtime + stage)
aws cloudfront describe-function \
  --name "ab-test-router" \
  --query 'FunctionSummary.{Runtime:FunctionConfig.Runtime,Stage:Stage,KeyValueStoreAssociations:KeyValueStoreAssociations}'

# Distribution function associations
aws cloudfront get-distribution-config \
  --id "$DIST_ID" \
  --query 'DistributionConfig.DefaultCacheBehavior.FunctionAssociations'
```

## Terraform equivalent

```hcl
# KVS store
resource "aws_cloudfront_key_value_store" "ab_testing" {
  name    = "ab-testing-kvs"
  comment = "A/B testing traffic split configuration"
}

# KVS keys (managed declaratively)
resource "aws_cloudfront_key_value_store_key" "traffic_split" {
  key_value_store_id = aws_cloudfront_key_value_store.ab_testing.id
  key                = "traffic-split"
  value              = "variant-b"
}

resource "aws_cloudfront_key_value_store_key" "ab_percentage" {
  key_value_store_id = aws_cloudfront_key_value_store.ab_testing.id
  key                = "ab-percentage"
  value              = "50"
}

# CloudFront Function (runtime must be cloudfront-js-2.0)
resource "aws_cloudfront_function" "ab_router" {
  name        = "ab-test-router"
  runtime     = "cloudfront-js-2.0"
  comment     = "A/B test router via KVS"
  publish     = true
  key_value_store_associations = [aws_cloudfront_key_value_store.ab_testing.arn]
  code        = <<-EOT
    import cf from 'cloudfront';
    const kvs = cf.openKvs();
    function handler(event) {
        const request = event.request;
        if (kvs.get('ab-active') !== 'true') return request;
        return request;
    }
  EOT
}
```

## AWS CLI quick reference

| Operation | Command |
|---|---|
| Create KVS store | `aws cloudfront create-key-value-store` |
| Describe KVS store | `aws cloudfront-keyvaluestore describe-key-value-store` |
| List KVS stores | `aws cloudfront list-key-value-stores` |
| Update KVS store | `aws cloudfront update-key-value-store` |
| Delete KVS store | `aws cloudfront delete-key-value-store` |
| Put key | `aws cloudfront-keyvaluestore put-key` |
| Get key | `aws cloudfront-keyvaluestore get-key` |
| List keys | `aws cloudfront-keyvaluestore list-keys` |
| Delete key | `aws cloudfront-keyvaluestore delete-key` |
| Create function | `aws cloudfront create-function` |
| Describe function | `aws cloudfront describe-function` |
| Test function | `aws cloudfront test-function` |
| Publish function | `aws cloudfront publish-function` |
| Update function | `aws cloudfront update-function` |
