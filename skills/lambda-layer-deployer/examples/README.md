# End-to-End Example: Lambda Layer Deployment

A walkthrough showing how to use the `lambda-layer-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a Python Lambda Layer with AWS Powertools and
common dependencies for arm64 functions. The layer needs:

- Layer name: my-powertools-layer
- Runtime: Python 3.10-3.13 (pure-Python deps, version-agnostic)
- Architecture: arm64 (Graviton)
- Dependencies: aws-lambda-powertools, boto3, requests
- License: MIT
- Attached to function: my-api-fn

Region: `us-east-1`
Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-lambda-layer
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Python Lambda Layer named my-powertools-layer in
      us-east-1 with aws-lambda-powertools, boto3, and requests.
      Compatible with python3.10 through 3.13 and arm64 only.
      Attach it to my-api-fn. Account: 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a lambda layer"
```

Output:

```
[Phase: Deploy | Skills routed: lambda-layer-deployer]

Primary route: lambda-layer-deployer (score: 22)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
LAMBDA_LAYER: my-powertools-layer
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Layer name: my-powertools-layer (region: us-east-1)
  [✓] Zip source: local (./layer/my-powertools-layer.zip)
  [✓] Zip structure: python/ (verified: pip install -t python/)
  [✓] Compatible runtimes: python3.10, python3.11, python3.12, python3.13
  [✓] Compatible architectures: arm64
  [✓] Layer size: 12.5 MB compressed (limit: 50 MB)
  [✓] Version: 1 (immutable; ARN: arn:aws:lambda:us-east-1:123456789012:layer:my-powertools-layer:1)
  [✓] License info: MIT
  [✓] Cross-account sharing: Same account (no sharing config needed)
  [✓] Function attachment: my-api-fn → layer version 1
VERIFICATION_COMMANDS:
  aws lambda list-layers
  aws lambda get-layer-version --layer-name my-powertools-layer --version-number 1
  aws lambda list-layer-versions --layer-name my-powertools-layer
  aws lambda get-function-configuration --function-name my-api-fn
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Build the layer zip
mkdir -p layer/python
pip install -t layer/python/ aws-lambda-powertools boto3 requests
cd layer
zip -r ../my-powertools-layer.zip python/
cd ..

# Step 2: Publish the layer version
LAYER_ARN=$(aws lambda publish-layer-version \
  --layer-name my-powertools-layer \
  --zip-file fileb://my-powertools-layer.zip \
  --compatible-runtimes python3.10 python3.11 python3.12 python3.13 \
  --compatible-architectures arm64 \
  --license-info "MIT" \
  --query LayerVersionArn --output text)

# Step 3: Attach to function
aws lambda update-function-configuration \
  --function-name my-api-fn \
  --layers "$LAYER_ARN"
```

---

## Step 4 — Post-deployment verification

```bash
# Layer version details — CompatibleRuntimes, CompatibleArchitectures
aws lambda get-layer-version --layer-name my-powertools-layer --version-number 1

# Function config — Layers array should include the layer ARN
aws lambda get-function-configuration --function-name my-api-fn \
  --query 'Layers'
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Architecture | Omits `--compatible-architectures` (defaults to x86_64) | Specifies `arm64` explicitly | arm64 functions reject x86_64 layers at attach time |
| Zip path | Zips the outer directory | `cd layer && zip -r ../layer.zip python/` | Wrong root = `/opt/layer/python/` instead of `/opt/python/` |
| Version pinning | Uses unqualified ARN | Uses version ARN (`:1`) | Lambda requires the version number |
| Runtime declaration | Omits compatible runtimes | Declares all four Python versions | Without runtimes, path resolution is not guaranteed |
| Auto-update assumption | Expects functions to auto-update | Explicit `update-function-configuration` | Layer versions are immutable; functions pin to a specific ARN |
| SDK bundling | Assumes AWS SDK is always bundled | Notes Node.js 22+ / Python 3.12+ don't bundle SDK | These runtimes require an SDK layer or bundled SDK |

---

## Related artifacts

- **Skill definition:** `skills/lambda-layer-deployer/SKILL.md`
- **Runtimes and architectures guide:** `skills/lambda-layer-deployer/references/runtimes-and-architectures.md`
- **Provisioning CLI commands:** `skills/lambda-layer-deployer/references/provisioning-cli-commands.md`
- **Slash command:** `commands/aws/deploy-lambda-layer.md`
- **Eval suite:** `skills/lambda-layer-deployer/evals/evals.json`
- **Legacy test cases:** `skills/lambda-layer-deployer/eval/test-cases.yaml`
