---
name: lambda-layer-deployer
description: 'Provisions AWS Lambda Layers with production defaults: layer creation (zip with dependencies), compatible runtimes (nodejs, python, java, ruby, provided.al2, provided.al2023), compatible architectures (x86_64, arm64), layer versioning (immutable versions), cross-account sharing (resource-based policy), layer usage (function + version ARN), AWS SDK layers (always latest runtime SDK), Powertools layers. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a Lambda Layer, packaging dependencies for Lambda, sharing a layer across accounts, pinning a layer version, or deploying Powertools / AWS SDK layers. Triggers: create Lambda layer, publish Lambda layer, Lambda layer version, Lambda layer zip, Lambda Powertools layer, Lambda SDK layer, Lambda layer compatible runtimes, Lambda layer arm64, Lambda layer cross-account.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with lambda, iam, and sts access. Works with Terraform aws_lambda_layer_version resource and CloudFormation AWS::Lambda::LayerVersion templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, lambda, lambda-layer, cloudops, deploy, compute, provisioning, layer-version, arm64, cross-account, powertools, sdk
  dependencies: aws-orchestrator
  keywords: aws, lambda, lambda layer, cloudops, deploy, provisioning, layer version, compatible runtimes, compatible architectures, arm64, x86_64, cross-account sharing, resource-based policy, powertools, aws sdk, dependencies, zip, nodejs, python, java, ruby, provided.al2, provided.al2023
  when_to_use: Invoke when the user wants to create or publish an AWS Lambda Layer (zip with dependencies), specify compatible runtimes and architectures, share a layer across accounts via resource-based policy, pin a layer version to a function, or deploy AWS-provided layers (Powertools, AWS SDK). Do NOT invoke for Lambda function deployment (use lambda-function-deployer), for container-based Lambda images (use container image workflows), or for Lambda runtime deprecation auditing (use lambda-runtime-deprecation- auditor).
---

# Lambda Layer Deployer

An AWS CloudOps agent skill that provisions AWS Lambda Layers with
correct defaults. The skill walks the operator through layer creation,
captures runtime, architecture, and sharing decisions, explains why
each default matters, and emits a READY_TO_DEPLOY checklist with copy-
pasteable verification commands.

## Activation keywords

create Lambda layer, publish Lambda layer, Lambda layer version,
Lambda layer zip, Lambda Powertools layer, Lambda SDK layer, Lambda
layer compatible runtimes, Lambda layer arm64, Lambda layer cross-
account, Lambda layer sharing, provided.al2 layer, provided.al2023
layer.

## STRICT output contract

When this skill is invoked with a Lambda-layer-provisioning request
(layer name, runtime, dependencies, architecture, sharing scope, or a
partial configuration), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in the "Output format" section using
the literal all-caps labels `LAMBDA_LAYER:`, `VERDICT:`, `CHECKLIST:`,
and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the checklist
(marked `[✗]`), and `READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Layer vs container image vs function bundle | Boundary call |
| Step 2 — Compatible runtimes (nodejs, python, java, ruby, provided) | Runtime scoping |
| Step 3 — Compatible architectures (x86_64, arm64) | Arch matching |
| Step 4 — Layer zip structure (per-runtime path conventions) | Packaging |
| Step 5 — Layer versioning (immutable versions, LatestVersionArn) | Versioning model |
| Step 6 — Cross-account sharing (resource-based policy) | Sharing scope |
| Step 7 — Attaching layers to functions (version ARN) | Usage |
| Step 8 — AWS-provided layers (SDK, Powertools) | Managed layers |
| Step 9 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/runtimes-and-architectures.md | Runtime + arch matrix detail |
| references/provisioning-cli-commands.md | Copy-pasteable CLI sequence |

## Mindset

**One-line takeaway:** A Lambda Layer is an immutable zip archive of
dependencies that Lambda extracts into `/opt` at runtime. It is NOT a
package manager, NOT a container image, and NOT mutable after publish.
Each publish creates a new immutable version; there is no in-place
update.

Three misconceptions dominate Lambda Layer misdesign at provisioning
time:

- **"Layers are mutable — I can update a layer in place."** They are
  not. Each `publish-layer-version` call creates a NEW immutable
  version with its own ARN. Functions reference a specific version
  ARN; they do NOT auto-update when a new version is published. To
  update a function's layer, you must update the function
  configuration with the new layer version ARN.

- **"One layer works for all runtimes."** A layer declares compatible
  runtimes AND compatible architectures. Lambda rejects attaching a
  layer to a function whose runtime or architecture does not match.
  A Python layer CANNOT be attached to a Node.js function; an x86_64
  layer CANNOT be attached to an arm64 function.

- **"The AWS SDK is always bundled."** Historically yes, but the
  Lambda runtime includes a specific SDK version that may lag. For
  the latest SDK features, use an AWS-provided SDK layer or bundle
  the SDK in your own layer / deployment package. Node.js 22+ and
  Python 3.12+ no longer bundle the full AWS SDK by default.

## Configuration dependency graph (novel heuristic)

Lambda Layer configurations are NOT independent. Many are immutable
after publish, others silently break function attachment. Use this
graph both to sequence provisioning and to debug "why can't I attach
this layer?" later.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Layer name | none — `publish` argument; must match `^[a-z0-9-_]+$` | name is region-scoped; versions append `:<n>` | version ARN |
| Zip content (S3 or local) | none — `publish` argument | zip structure MUST match runtime path convention or Lambda silently ignores the content | `/opt` extraction at runtime |
| Compatible runtimes | none — `publish` argument | attaching to a function with a non-matching runtime fails with `ResourceConflictException` | runtime-scoped attachment |
| Compatible architectures | none — `publish` argument (default: x86_64) | attaching to a function with a non-matching architecture fails with `ResourceConflictException` | arch-scoped attachment |
| License info | none — optional `--license-info` | text only; no enforcement | compliance metadata |
| Layer version | created on each `publish` call | **IMMUTABLE** — cannot be modified or deleted (only the entire layer can be deleted, removing all versions) | versioned ARN for function attachment |
| Resource-based policy (sharing) | layer exists; `add-permission` call | policy is per-version; each version needs its own permission if shared individually | cross-account / Organization-wide sharing |
| Function attachment | function exists; layer runtime + arch match function | function config update needed when a new layer version is published | `/opt` content available at runtime |

**The immutable rows are the ones a baseline model misses.** Layer
versions are immutable — there is no "update the layer." Each publish
is a new version. Functions pinned to a version ARN do NOT see new
versions until the function configuration is explicitly updated.

**Cross-dependency gotchas:**
- A layer published WITHOUT specifying compatible architectures
  defaults to x86_64. It will FAIL to attach to an arm64 function.
  Always specify `--compatible-architectures` explicitly.
- A layer published WITHOUT specifying compatible runtimes can be
  attached to ANY runtime function — but Lambda will NOT guarantee
  correct `/opt` path resolution. Always specify runtimes explicitly.
- Cross-account sharing requires BOTH a resource-based policy on the
  layer version AND the consuming account's IAM role to have
  `lambda:GetLayerVersion` permission.
- Layer size limit: 50 MB per layer (compressed), 250 MB total per
  function (all layers + deployment package, uncompressed). A layer
  that is too large silently pushes the function over the total.

## Expert heuristic: layer zip path conventions

Lambda extracts the layer zip into `/opt` at runtime. Each runtime
expects dependencies in a specific path inside the zip. A baseline
model says "zip your dependencies"; this heuristic gives the exact
path mapping.

```text
Python (all versions):
  zip path:   python/                 (or python/lib/python3.x/site-packages/)
  runtime:    /opt/python/...
  packages:   pip install -t python/ <pkg>

Node.js (all versions):
  zip path:   nodejs/node_modules/
  runtime:    /opt/nodejs/node_modules/
  packages:   npm install --prefix nodejs/ <pkg>

Java:
  zip path:   java/lib/
  runtime:    /opt/java/lib/
  packages:   jar files placed in java/lib/

Ruby:
  zip path:   ruby/gems/  (or ruby/lib/)
  runtime:    /opt/ruby/gems/...
  packages:   gem install --install-dir ruby/gems/ <gem>

provided.al2 / provided.al2023:
  zip path:   bin/  lib/  (or any custom path)
  runtime:    /opt/bin/  /opt/lib/
  packages:   custom binaries or shared libraries
```

**Common mistake:** zipping dependencies at the wrong path. A Python
layer zipped as `site-packages/requests/` instead of
`python/requests/` will be extracted to `/opt/site-packages/` which
Python does not search. The layer attaches but imports fail at
runtime with `ModuleNotFoundError`.

## Expert heuristic: layer version lifecycle

Layer versions are the core abstraction. Understanding the lifecycle
prevents the most common layer-related production incidents.

```text
publish-layer-version  →  creates version N (immutable)
                           ARN: arn:aws:lambda:<region>:<acct>:layer:<name>:N

function update        →  attaches version N's ARN to function
                           function.config.Layers = [<arn>:N]

publish-layer-version  →  creates version N+1 (immutable, separate ARN)
                           functions still point to version N (NO auto-update)

function update        →  re-point to version N+1's ARN
                           (explicit; no rolling update)

delete-layer-version   →  removes version N (CANNOT if a function
                           references it — must detach first)
```

**Key implication:** there is no "latest" alias for layers in the
same way as Lambda function aliases. `LatestVersionArn` is a
convenience field but functions must be explicitly updated to use it.
A common production pattern is to update the function's layer
configuration in the same deployment step that publishes the new
layer version.

## Expert heuristic: cross-account sharing matrix

Cross-account layer sharing involves two sides: the layer owner
(resource-based policy) and the consumer (IAM policy). A baseline
model says "share the layer"; this matrix shows the full
requirements.

| Sharing scope | Owner-side (resource-based policy) | Consumer-side (IAM) | Notes |
|---|---|---|---|
| Same account | Not required (implicit) | IAM role has `lambda:GetLayerVersion` | Default; no sharing config needed |
| Specific external account | `add-permission` with `--principal <acct-id>` | Consumer role has `lambda:GetLayerVersion` on the layer ARN | Most common cross-account pattern |
| Entire Organization | `add-permission` with `--principal '*'` and `--organization-id <org-id>` | Consumer role has `lambda:GetLayerVersion` | Requires AWS Organizations; org ID verified at attach time |
| Public (all accounts) | `add-permission` with `--principal '*'` (NO org ID) | Any account with `lambda:GetLayerVersion` | AVOID for proprietary code; appropriate for open-source utility layers |
| Service-level (e.g., Lambda@Edge) | Must be in us-east-1 | Consumer function must be in us-east-1 | Lambda@Edge layers must be in us-east-1 |

**Common mistake:** adding the resource-based policy but forgetting
the consumer-side IAM permission. The consumer gets
`AccessDeniedException` when trying to attach the layer. Both sides
are required.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING** with a
specific gap citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS account with Lambda access | Can't provision without it | `aws sts get-caller-identity` |
| Region selected | Layers are region-scoped (except Lambda@Edge) | `aws configure get region` |
| Runtime(s) identified | Layer must declare compatible runtimes; mismatched attachment fails | Confirm target function runtimes |
| Architecture(s) identified | Layer must declare compatible architectures; default is x86_64 | Confirm target function architecture |
| Dependencies packaged in correct zip path | Wrong path = layer attaches but imports fail at runtime | Verify zip structure per runtime (see Expert heuristic) |
| Layer size within limits | 50 MB per layer (compressed); 250 MB total per function | `du -sh layer.zip` |
| IAM permissions for sharing (if cross-account) | Resource-based policy needs `lambda:AddPermission`; consumer needs `lambda:GetLayerVersion` | Verify IAM policy attached to consuming role |
| Layer name unique in this region | Names are region-unique; versions append | `aws lambda list-layers` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Layer vs container image vs function bundle

The first decision is whether a Lambda Layer is the right packaging
mechanism. Lambda supports three deployment models: zip function
bundle, Lambda Layer, and container image.

**Decision tree:**

```text
Are the dependencies shared across multiple functions?
├── YES → Are they runtime-specific (Python, Node, etc.)?
│   ├── YES → Lambda Layer  (this skill)
│   │         Shared zip of dependencies, extracted to /opt
│   └── NO  → Container image  (NOT this skill)
│             Full container with OS, runtime, dependencies
└── NO  → Are the dependencies > 250 MB uncompressed?
    ├── YES → Container image  (NOT this skill)
    │         Up to 10 GB image size
    └── NO  → Function deployment package  (lambda-function-deployer)
              Dependencies bundled directly in the function zip
```

**Feature comparison:**

| Feature | Lambda Layer | Container Image | Function Bundle |
|---|---|---|---|
| Max size | 50 MB compressed per layer; 250 MB total | 10 GB | 50 MB compressed; 250 MB total |
| Sharing | Cross-account via resource-based policy | ECR repository policy | Per-function only |
| Versioning | Immutable versions | ECR image tags | Per-function versions |
| `/opt` extraction | Yes | No (custom paths) | No (inline) |
| Runtime matching | Required (compatible runtimes) | Not required | Implicit (same as function) |
| Cold start impact | Minimal (pre-extracted) | Higher (container init) | Minimal |

**Common mistake:** using a layer for single-function dependencies.
Layers add versioning complexity without benefit when only one
function uses them. Bundle directly in the function package instead.

## Step 2 — Compatible runtimes

A Lambda Layer declares which runtimes it is compatible with. Lambda
enforces this at attach time — a mismatch causes
`ResourceConflictException`.

**Supported runtimes:**

| Runtime family | Values | Notes |
|---|---|---|
| Python | `python3.10`, `python3.11`, `python3.12`, `python3.13` | `pip install -t python/` |
| Node.js | `nodejs18.x`, `nodejs20.x`, `nodejs22.x` | `npm install --prefix nodejs/` |
| Java | `java17`, `java21` | jar files in `java/lib/` |
| Ruby | `ruby3.2`, `ruby3.3`, `ruby3.4` | `gem install --install-dir ruby/gems/` |
| Provided (custom) | `provided.al2`, `provided.al2023` | Custom runtime; binaries in `bin/`, `lib/` |

**Best practices:**
- Declare ALL compatible runtimes explicitly. A Python layer should
  list `python3.10 python3.11 python3.12 python3.13` if the
  dependencies are pure-Python and version-agnostic.
- For compiled extensions (C/Fortran), the layer may be specific to
  one runtime version (e.g., NumPy with a specific Python ABI).
- `provided.al2` (Amazon Linux 2) and `provided.al2023` (Amazon
  Linux 2023) are for custom runtimes (Go, Rust, etc.) — binaries
  must be compiled for the target OS and architecture.

**Common mistake:** declaring no compatible runtimes. Lambda allows
it, but the layer may be attached to any function without validation.
Runtime-specific path resolution is NOT guaranteed. Always specify
runtimes explicitly.

## Step 3 — Compatible architectures

A Lambda Layer declares which architectures it is compatible with.
The default is `x86_64` if not specified. Lambda enforces this at
attach time.

**Supported architectures:**

| Architecture | Values | Notes |
|---|---|---|
| x86_64 | `x86_64` | Default; Intel/AMD x86_64 |
| arm64 | `arm64` | AWS Graviton; lower cost, better perf for many workloads |

**Key rules:**
- A layer published for `x86_64` CANNOT be attached to an `arm64`
  function (and vice versa).
- For pure-Python / pure-JS layers, the architecture may not matter
  (interpreted code), but Lambda still enforces the declaration.
- For compiled code (C extensions, Go binaries, Rust binaries), the
  architecture MUST match. A binary compiled for x86_64 will crash
  on arm64 (illegal instruction).

**Common mistake:** publishing a layer without `--compatible-
architectures` and then trying to attach it to an arm64 function.
The default is x86_64. Always specify architectures explicitly,
especially for layers containing compiled code.

## Step 4 — Layer zip structure (per-runtime path conventions)

Lambda extracts the layer zip into `/opt` at runtime. Each runtime
has a specific expected path. See the Expert heuristic above for the
full path mapping.

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

## Step 5 — Layer versioning (immutable versions)

Each `publish-layer-version` call creates a new immutable version.
Versions are numbered sequentially starting from 1.

**Version lifecycle:**
- Version N is immutable — it cannot be modified.
- Version N's ARN is `arn:aws:lambda:<region>:<acct>:layer:<name>:N`.
- `LatestVersionVersion` is a convenience field pointing to the
  highest version number, but functions do NOT auto-update.
- Deleting a version requires that NO function references it.
- Deleting the entire layer removes ALL versions.

**Versioning strategy:**
- Each meaningful change to dependencies = new version publish.
- Pin functions to a specific version ARN for reproducibility.
- Update function configuration in the same deployment step as the
  new layer version publish.
- Use `LatestVersionArn` for dev / test functions that should track
  the latest.

**Common mistake:** publishing a new layer version and expecting
functions to auto-update. They do NOT. Each function must be
explicitly updated with `update-function-configuration --layers`.

## Step 6 — Cross-account sharing (resource-based policy)

Cross-account layer sharing uses a resource-based policy on the layer
version. The consuming account also needs IAM permission.

**Share with a specific account:**

```bash
aws lambda add-permission \
  --layer-name my-shared-layer \
  --statement-id share-with-123456789012 \
  --action lambda:GetLayerVersion \
  --principal 123456789012 \
  --version-number 1
```

**Share with an entire Organization:**

```bash
aws lambda add-permission \
  --layer-name my-org-layer \
  --statement-id share-with-org \
  --action lambda:GetLayerVersion \
  --principal '*' \
  --organization-id o-abc123def \
  --version-number 1
```

**Consumer-side (in the consuming account):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "lambda:GetLayerVersion",
      "Resource": "arn:aws:lambda:us-east-1:111111111111:layer:my-shared-layer:*"
    }
  ]
}
```

**Common mistake:** adding the resource-based policy but forgetting
the consumer-side IAM permission. Both sides are required.

## Step 7 — Attaching layers to functions (version ARN)

A function references layers by their version ARN (not the layer
name or unqualified ARN).

```bash
aws lambda update-function-configuration \
  --function-name my-function \
  --layers "arn:aws:lambda:us-east-1:111111111111:layer:my-layer:1"
```

**Multiple layers:**

```bash
aws lambda update-function-configuration \
  --function-name my-function \
  --layers \
    "arn:aws:lambda:us-east-1:111111111111:layer:base-deps:3" \
    "arn:aws:lambda:us-east-1:111111111111:layer:powertools:1"
```

**Order matters:** when multiple layers define the same file path,
the LAST layer in the list takes precedence (it overwrites earlier
extractions).

**Common mistake:** using the unqualified ARN (without `:N`). Lambda
requires the version number. `arn:...:layer:my-layer` will fail;
`arn:...:layer:my-layer:1` will work.

## Step 8 — AWS-provided layers (SDK, Powertools)

AWS provides managed layers that are maintained and updated by AWS.
These are useful for always having the latest SDK or Powertools
without managing your own layer.

**AWS Powertools for Python:**

```bash
# Get the latest Powertools layer ARN for your region
aws lambda list-layers --query 'Layers[?contains(LayerName, `AWSLambdaPowertools`)]'

# Or use the well-known ARN (region-specific; check docs)
# Example us-east-1:
# arn:aws:lambda:us-east-1:017000801446:layer:AWSLambdaPowertoolsPythonV3:1
```

**AWS Powertools for Node.js:**

```bash
# Node.js Powertools layer (region-specific ARN)
# Example us-east-1:
# arn:aws:lambda:us-east-1:094274105915:layer:AWSLambdaPowertoolsTypeScript:1
```

**AWS SDK layers:**
- Node.js 22+ and Python 3.12+ no longer bundle the full AWS SDK.
- Use the AWS-provided SDK layer or bundle the SDK in your
  deployment package.
- The AWS SDK layer is updated by AWS and always includes the latest
  version for the declared runtime.

**Common mistake:** assuming the AWS SDK is always bundled. For
Node.js 22+ and Python 3.12+, the SDK is NOT bundled by default.
Either attach an SDK layer or include it in your deployment package.

## Step 9 — Recent features

**Recent AWS features (2023-2026):**
- **Powertools V3 (2024-2025):** AWS Lambda Powertools for Python
  V3 released; improved tracing, metrics, logging, and idempotency.
- **Node.js 22 support (2024-2025):** Node.js 22 runtime; no bundled
  AWS SDK by default (use SDK layer or bundle).
- **Python 3.13 support (2024-2025):** Python 3.13 runtime; no
  bundled AWS SDK by default.
- **provided.al2023 (Amazon Linux 2023):** Updated custom runtime
  base; newer packages, glibc version, and security patches.
- **Graviton (arm64) expansion (2023-2024):** arm64 generally
  available for all runtimes; up to 34% better price-performance.
- **Lambda Insights (deprecated):** CloudWatch Lambda Insights
  extension layer deprecated in favor of built-in CloudWatch
  Application Signals (2024-2025).

## NEVER do these things

1. **NEVER publish a layer without specifying compatible runtimes.**
   Without runtimes, Lambda allows attachment to any function but
   does NOT guarantee `/opt` path resolution. Always declare
   `--compatible-runtimes`.

2. **NEVER publish a layer without specifying compatible
   architectures.** The default is x86_64. A layer intended for
   arm64 functions will fail to attach if you omit
   `--compatible-architectures arm64`.

3. **NEVER zip the outer directory.** `zip -r layer.zip layer/`
   creates `layer/python/...` inside the zip — Lambda extracts to
   `/opt/layer/python/` which Python does not search. Always `cd`
   into the directory and zip from inside.

4. **NEVER assume functions auto-update when a new layer version is
   published.** Layer versions are immutable; functions pin to a
   specific version ARN. Each new version requires an explicit
   `update-function-configuration --layers` call.

5. **NEVER share a layer publicly with `--principal '*'` for
   proprietary code.** Public sharing grants `lambda:GetLayerVersion`
   to ALL AWS accounts. Only share publicly for open-source utility
   layers.

6. **NEVER forget the consumer-side IAM permission for cross-account
   sharing.** The resource-based policy on the layer is necessary
   but NOT sufficient. The consuming role must also have
   `lambda:GetLayerVersion`.

7. **NEVER use the unqualified layer ARN when attaching to a
   function.** Lambda requires the version number:
   `arn:...:layer:my-layer:1`, NOT `arn:...:layer:my-layer`.

8. **NEVER exceed 250 MB total (all layers + function package,
   uncompressed).** Each layer can be up to 50 MB compressed, but
   the function's total deployment size (all layers + code,
   uncompressed) has a hard limit of 250 MB.

9. **NEVER delete a layer version that a function references.**
   `delete-layer-version` will fail with `ResourceInUseException`.
   Detach the layer from ALL functions before deleting.

10. **NEVER assume the AWS SDK is bundled for Node.js 22+ or Python
    3.12+.** These runtimes do NOT bundle the full AWS SDK. Attach
    an SDK layer or bundle it in your deployment package.

11. **NEVER use `provided.al2` layers on `provided.al2023` functions
    without testing.** The underlying OS (AL2 vs AL2023) has
    different glibc versions and package availability. Compiled
    binaries may not be compatible across the two.

12. **NEVER ignore layer ordering.** When multiple layers define the
    same file path, the LAST layer in the list takes precedence.
    Order layers from least-specific to most-specific.

## Output format

```text
LAMBDA_LAYER: <layer-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Layer name: <name> (region: <region>)
  [✓|✗] Zip source: <local-path | s3-uri>
  [✓|✗] Zip structure: <runtime>/... (verified path convention)
  [✓|✗] Compatible runtimes: <runtimes>
  [✓|✗] Compatible architectures: <x86_64 | arm64 | both>
  [✓|✗] Layer size: <size> MB compressed (limit: 50 MB)
  [✓|✗] Version: <N> (immutable; ARN: arn:aws:lambda:<region>:<acct>:layer:<name>:<N>)
  [✓|✗] License info: <text | none>
  [✓|✗] Cross-account sharing: <scope> (resource-based policy + consumer IAM)
  [✓|✗] Function attachment: <function-name> → layer version <N>
VERIFICATION_COMMANDS:
  aws lambda list-layers
  aws lambda get-layer-version --layer-name <name> --version-number <N>
  aws lambda list-layer-versions --layer-name <name>
  aws lambda get-layer-version-policy --layer-name <name>
  aws lambda get-function-configuration --function-name <function>
```

### Worked example — Python Powertools layer with arm64

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

## Error handling

### Layer attach fails (`ResourceConflictException`)

**Cause:** the layer's compatible runtimes or architectures do not
match the function's runtime or architecture.

**Fix:** verify the function's runtime and architecture via
`get-function-configuration`, then re-publish the layer with the
correct `--compatible-runtimes` and `--compatible-architectures`.

### Import fails at runtime (`ModuleNotFoundError`)

**Cause:** the layer zip structure does not match the runtime's
expected path.

**Fix:** verify the zip structure. For Python, dependencies must be
in `python/`. For Node.js, in `nodejs/node_modules/`. Re-zip from
inside the directory so the runtime path is at the zip root.

### Cross-account attach fails (`AccessDeniedException`)

**Cause:** either the resource-based policy is missing on the layer,
or the consuming role lacks `lambda:GetLayerVersion` permission.

**Fix:** verify both sides — `get-layer-version-policy` on the owner
side, and the consuming role's IAM policy. Both are required.

### Layer publish fails (`ResourceConflictException` on size)

**Cause:** the compressed zip exceeds 50 MB, or the total function
deployment size exceeds 250 MB.

**Fix:** reduce the layer size (remove unused dependencies, strip
debug symbols). If the dependency set is too large, switch to a
container image deployment.

## Domain

AWS CloudOps / AWS Lambda Layer Provisioning & Dependency Management.

## AWS documentation

- **AWS Lambda Developer Guide — Layers** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html
- **Lambda layer paths** — https://docs.aws.amazon.com/lambda/latest/dg/packaging-layers.html
- **Sharing layers cross-account** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html#configuration-layers-permissions
- **Lambda Powertools** — https://docs.powertools.aws.dev/
- **Lambda runtimes** — https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html
- **Lambda arm64 (Graviton)** — https://docs.aws.amazon.com/lambda/latest/dg/lambda-arm64.html
- **provided.al2023** — https://docs.aws.amazon.com/lambda/latest/dg/runtimes-custom.html
