# Provisioning CLI Commands — Lambda Layer Deployer

Full copy-pasteable CLI command sequence for provisioning AWS Lambda
Layers with correct runtimes, architectures, versioning, and cross-
account sharing. Variables to substitute: `<layer>`, `<region>`,
`<account-id>`, zip path, runtime, architecture.

## Step 0: Prerequisites check

```bash
# Confirm caller identity
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"

# Confirm region
REGION=$(aws configure get region)
echo "Region: $REGION"

# Confirm layer name is available (or will be a new layer)
aws lambda list-layers --query 'Layers[?LayerName==`<layer>`]'
```

## Step 1: Build the layer zip (Python example)

```bash
# Create the layer directory structure
mkdir -p layer/python

# Install dependencies into the correct path
pip install -t layer/python/ \
  aws-lambda-powertools \
  boto3 \
  requests

# Optional: strip debug symbols to reduce size
find layer/python -name "*.so" -exec strip {} \; 2>/dev/null || true

# Zip from inside the directory (python/ must be at the zip root)
cd layer
zip -r ../<layer>.zip python/
cd ..

# Verify the zip structure
unzip -l <layer>.zip | head -10
# Expected: python/ at the root, NOT layer/python/
```

## Step 1 alt: Build the layer zip (Node.js example)

```bash
mkdir -p layer/nodejs
cd layer/nodejs
npm init -y
npm install @aws-sdk/client-s3 @aws-sdk/client-dynamodb
cd ..
zip -r ../<layer>.zip nodejs/
cd ..
```

## Step 1 alt: Build the layer zip (provided.al2023 Go example)

```bash
mkdir -p layer/bin
# Compile the Go binary for arm64 (Graviton)
GOOS=linux GOARCH=arm64 go build -o layer/bin/bootstrap main.go
cd layer
zip -r ../<layer>.zip bin/
cd ..
```

## Step 2: Publish the layer version

```bash
aws lambda publish-layer-version \
  --layer-name <layer> \
  --zip-file fileb://<layer>.zip \
  --compatible-runtimes python3.10 python3.11 python3.12 python3.13 \
  --compatible-architectures arm64 \
  --license-info "MIT" \
  --description "Python dependencies: Powertools, boto3, requests"
```

Capture the version ARN from the output:

```bash
LAYER_ARN=$(aws lambda publish-layer-version \
  --layer-name <layer> \
  --zip-file fileb://<layer>.zip \
  --compatible-runtimes python3.10 python3.11 python3.12 python3.13 \
  --compatible-architectures arm64 \
  --query LayerVersionArn --output text)
echo "Layer ARN: $LAYER_ARN"
```

## Step 3: Attach the layer to a function

```bash
aws lambda update-function-configuration \
  --function-name <function> \
  --layers "$LAYER_ARN"
```

**Multiple layers (order matters — last takes precedence on path conflicts):**

```bash
aws lambda update-function-configuration \
  --function-name <function> \
  --layers \
    "arn:aws:lambda:us-east-1:<account-id>:layer:base-deps:3" \
    "$LAYER_ARN"
```

## Step 4: Share the layer cross-account (optional)

### Share with a specific account

```bash
aws lambda add-permission \
  --layer-name <layer> \
  --statement-id share-with-<consumer-account> \
  --action lambda:GetLayerVersion \
  --principal <consumer-account-id> \
  --version-number <N>
```

### Share with an Organization

```bash
aws lambda add-permission \
  --layer-name <layer> \
  --statement-id share-with-org \
  --action lambda:GetLayerVersion \
  --principal '*' \
  --organization-id o-<org-id> \
  --version-number <N>
```

### Verify the resource-based policy

```bash
aws lambda get-layer-version-policy --layer-name <layer> --version-number <N>
```

## Step 5: Publish a new version (update dependencies)

```bash
# Rebuild the zip with updated dependencies
pip install -t layer/python/ --upgrade aws-lambda-powertools
cd layer && zip -r ../<layer>-v2.zip python/ && cd ..

# Publish version N+1
aws lambda publish-layer-version \
  --layer-name <layer> \
  --zip-file fileb://<layer>-v2.zip \
  --compatible-runtimes python3.10 python3.11 python3.12 python3.13 \
  --compatible-architectures arm64

# Update the function to point to the new version (NOT automatic)
NEW_ARN=$(aws lambda list-layer-versions --layer-name <layer> \
  --query 'max_by(LayerVersions, &Version).LayerVersionArn' --output text)

aws lambda update-function-configuration \
  --function-name <function> \
  --layers "$NEW_ARN"
```

## Step 6: Use AWS-provided layers (Powertools, SDK)

```bash
# List AWS-provided layers in your region
aws lambda list-layers \
  --query 'Layers[?contains(LayerName, `AWSLambdaPowertools`)]'

# Attach the Powertools layer (use the region-specific ARN from docs)
aws lambda update-function-configuration \
  --function-name <function> \
  --layers \
    "arn:aws:lambda:us-east-1:017000801446:layer:AWSLambdaPowertoolsPythonV3:1"
```

## Verification

```bash
# List all layers in the region
aws lambda list-layers

# Get details of a specific layer version
aws lambda get-layer-version --layer-name <layer> --version-number <N>

# List all versions of a layer
aws lambda list-layer-versions --layer-name <layer>

# Get the resource-based policy (sharing config)
aws lambda get-layer-version-policy --layer-name <layer> --version-number <N>

# Verify the function has the layer attached
aws lambda get-function-configuration --function-name <function> \
  --query 'Layers'
```

## Terraform equivalent (aws_lambda_layer_version)

```hcl
resource "aws_lambda_layer_version" "deps" {
  layer_name          = "<layer>"
  filename            = "<layer>.zip"
  source_code_hash    = filebase64sha256("<layer>.zip")
  compatible_runtimes = ["python3.10", "python3.11", "python3.12", "python3.13"]
  compatible_architectures = ["arm64"]
  license_info        = "MIT"
  description         = "Python dependencies: Powertools, boto3, requests"
}

resource "aws_lambda_function" "api" {
  function_name = "<function>"
  # ... other config ...
  layers = [aws_lambda_layer_version.deps.arn]
}

# Cross-account sharing
resource "aws_lambda_permission" "share" {
  layer_name        = aws_lambda_layer_version.deps.layer_name
  version_number    = aws_lambda_layer_version.deps.version
  statement_id      = "share-with-consumer"
  action            = "lambda:GetLayerVersion"
  principal         = "<consumer-account-id>"
}
```

## AWS CLI quick reference

| Operation | Command |
|---|---|
| Publish layer version | `aws lambda publish-layer-version` |
| List layers | `aws lambda list-layers` |
| List layer versions | `aws lambda list-layer-versions` |
| Get layer version | `aws lambda get-layer-version` |
| Get layer policy | `aws lambda get-layer-version-policy` |
| Add permission (share) | `aws lambda add-permission` |
| Remove permission | `aws lambda remove-permission` |
| Delete layer version | `aws lambda delete-layer-version` |
| Attach to function | `aws lambda update-function-configuration --layers` |

---

### ## Step 4 — Layer zip structure (per-runtime path conventions) — packaging examples

**Python example:**

```bash
# Create the layer directory structure
mkdir -p layer/python
pip install -t layer/python/ requests boto3-Powertools

# Zip from inside the directory (so python/ is at the zip root)
cd layer
zip -r ../my-python-layer.zip python/
cd ..
```

**Node.js example:**

```bash
mkdir -p layer/nodejs
cd layer/nodejs
npm init -y
npm install @aws-sdk/client-s3
cd ..
zip -r ../my-node-layer.zip nodejs/
cd ..
```

**provided.al2 example (Go binary):**

```bash
mkdir -p layer/bin
cp bootstrap layer/bin/
cd layer
zip -r ../my-go-layer.zip bin/
cd ..
```

**Common mistake:** zipping the outer directory instead of from
inside it. `zip -r layer.zip layer/` creates a zip with `layer/` as
the root — Lambda extracts to `/opt/layer/python/` instead of
`/opt/python/`. Always `cd` into the directory before zipping.

### Step 8 — AWS Powertools for Python layer ARN lookup


```bash
# Get the latest Powertools layer ARN for your region
aws lambda list-layers --query 'Layers[?contains(LayerName, `AWSLambdaPowertools`)]'

# Or use the well-known ARN (region-specific; check docs)
# Example us-east-1:
# arn:aws:lambda:us-east-1:017000801446:layer:AWSLambdaPowertoolsPythonV3:1
```

### Step 8 — AWS Powertools for Node.js layer ARN lookup


```bash
# Node.js Powertools layer (region-specific ARN)
# Example us-east-1:
# arn:aws:lambda:us-east-1:094274105915:layer:AWSLambdaPowertoolsTypeScript:1
```
