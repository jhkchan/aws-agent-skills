# Advanced Patterns — Lambda Layer Deployer

Deep-dive material moved verbatim from SKILL.md: configuration dependency
graph, expert heuristics, feature comparison, and recent AWS features.
Load on demand.

### Configuration dependency graph (novel heuristic)


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

### Expert heuristic: layer zip path conventions


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

### Expert heuristic: layer version lifecycle


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

### Expert heuristic: cross-account sharing matrix


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

### Step 1 — Feature comparison: Lambda Layer vs container image vs function bundle

**Feature comparison:**

| Feature | Lambda Layer | Container Image | Function Bundle |
|---|---|---|---|
| Max size | 50 MB compressed per layer; 250 MB total | 10 GB | 50 MB compressed; 250 MB total |
| Sharing | Cross-account via resource-based policy | ECR repository policy | Per-function only |
| Versioning | Immutable versions | ECR image tags | Per-function versions |
| `/opt` extraction | Yes | No (custom paths) | No (inline) |
| Runtime matching | Required (compatible runtimes) | Not required | Implicit (same as function) |
| Cold start impact | Minimal (pre-extracted) | Higher (container init) | Minimal |

### Step 9 — Recent features


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
