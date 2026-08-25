# Component Recipe and Lifecycle Hooks — Greengrass Component Deployer

Deep reference on component recipe structure, lifecycle hook
semantics (install, startup, shutdown, recover), artifact path
variables, platform-specific manifests, and recipe validation.
Loaded on demand by the skill — kept out of the main SKILL.md body
so the provisioning procedure stays scannable.

## Recipe structure (full schema)

### Top-level fields

| Field | Required | Description |
|---|---|---|
| RecipeFormatVersion | YES | Always `2020-01-25` |
| ComponentName | YES | Reverse-DNS name (e.g., `com.example.MyComponent`) |
| ComponentVersion | YES | Semantic version (e.g., `1.0.0`) |
| ComponentDescription | No | Human-readable description |
| ComponentPublisher | YES | Publisher name |
| ComponentConfiguration | No | Default configuration schema |
| ComponentDependencies | No | HARD/SOFT dependencies |
| Manifests | YES | Platform-specific artifacts and lifecycle |

### Complete recipe example

```yaml
---
RecipeFormatVersion: "2020-01-25"
ComponentName: com.example.DataProcessor
ComponentVersion: "2.1.0"
ComponentDescription: "Edge data processor with configuration merge"
ComponentPublisher: Example
ComponentConfiguration:
  DefaultConfiguration:
    sampleRate: 1000
    outputPath: "/greengrass/v2/work/com.example.DataProcessor/output"
    logging:
      level: "info"
      maxSizeMB: 10
    features:
      enableCompression: false
      enableEncryption: true
ComponentDependencies:
  - DependencyType: HARD
    ComponentRequire:
      ThingName: aws.lambda
      Version: "2.3.0"
  - DependencyType: SOFT
    ComponentRequire:
      ThingName: com.example.MetricsCollector
      Version: "1.0.0"
Manifests:
  - Name: "linux-amd64"
    Platform:
      architecture: amd64
      os: linux
    Artifacts:
      - URI: s3://my-bucket/artifacts/com.example.DataProcessor/2.1.0/processor.zip
        Unarchive: ZIP
        Digest: "SHA256:abc123..."
    Lifecycle:
      Install:
        Script: |
          echo "Installing DataProcessor 2.1.0"
          mkdir -p {work:path}/output
      Startup:
        Script: |
          #!/bin/bash
          cd {artifacts:decompressedPath}/processor
          RATE={configuration:/sampleRate}
          OUTPUT={configuration:/outputPath}
          LEVEL={configuration:/logging/level}
          # Long-running process — stays alive
          python3 main.py --rate "$RATE" --output "$OUTPUT" --log-level "$LEVEL"
      Shutdown:
        Script: |
          echo "Shutting down DataProcessor"
          # Kill any background processes
          pkill -f "main.py" || true
      Recover:
        Script: |
          echo "Startup failed, retrying..."
          sleep 5
```

## Lifecycle hook semantics

### Install hook

Runs ONCE when the component is first deployed or when the version
changes. Use for:

- Extracting artifacts (ZIP/TAR archives)
- Creating directories
- Installing dependencies (apt, pip, etc.)
- Setting permissions

```yaml
Lifecycle:
  Install:
    Script: |
      # Extract the archive (Unarchive: ZIP handles this, but you can do more)
      mkdir -p {work:path}/data
      chmod 755 {artifacts:decompressedPath}/processor/run.sh
```

**Exit code behavior:**
- Exit 0: Install succeeds, proceed to Startup.
- Exit non-zero: Component deployment FAILS. The entire deployment
  may roll back (depending on failureDetectionPolicy).

### Startup hook

Runs EVERY TIME the component starts (after install, on device boot,
on manual restart, on recovery). Use for:

- Running the main component logic
- Starting daemons, servers, loops
- Long-running processes

```yaml
Lifecycle:
  Startup:
    Script: |
      #!/bin/bash
      # This MUST be a long-running process
      python3 {artifacts:decompressedPath}/processor/server.py
```

**Critical:** if the startup script exits immediately (e.g., it runs
a one-shot command and exits), Greengrass considers the component
"errored" and restarts it in a loop. For one-shot tasks, use the
install hook instead.

**Exit code behavior:**
- Exit 0: Component is RUNNING. Greengrass monitors the process.
  If it exits, Greengrass runs the recover hook (if defined), then
  restarts.
- Exit non-zero: Component enters ERRORED state. Recover hook runs
  (if defined). After recover, startup retries.

**Timeout:** default 60 seconds. If startup does not complete within
the timeout, Greengrass considers it failed. Override with:

```yaml
Startup:
  Timeout: 300
  Script: |
    # Long startup that may take > 60s
```

### Shutdown hook

Runs when the component stops (undeploy, device shutdown, version
update). Use for:

- Killing processes
- Flushing buffers
- Closing connections
- Releasing resources

```yaml
Lifecycle:
  Shutdown:
    Script: |
      pkill -f "server.py" || true
      echo "Clean shutdown complete"
```

**Exit code behavior:**
- Exit 0: Clean stop.
- Exit non-zero or timeout: Greengrass force-kills the component.

### Recover hook (optional)

Runs if the startup hook fails. Use for:

- Retry logic
- Fallback behavior
- Cleanup before retry

```yaml
Lifecycle:
  Recover:
    Script: |
      echo "Startup failed at $(date)"
      # Clean up partial state
      rm -f {work:path}/output/*.tmp
      # Greengrass will retry startup after recover exits
```

## Artifact path variables

| Variable | Description | Example value |
|---|---|---|
| `{artifacts:path}` | Path to downloaded artifact (file or dir) | `/greengrass/v2/packages/artifacts/com.example.DataProcessor/2.1.0/processor.zip` |
| `{artifacts:decompressedPath}` | Path to decompressed artifact | `/greengrass/v2/packages/artifacts/com.example.DataProcessor/2.1.0/processor/` |
| `{work:path}` | Component work directory (persistent) | `/greengrass/v2/work/com.example.DataProcessor/` |
| `{configuration:/key}` | Configuration value | Value of the `key` from merged config |
| `{configuration:/nested/key}` | Nested configuration value | Value of `nested.key` |

## Platform-specific manifests

A recipe can define multiple manifests for different platforms.
Greengrass selects the matching manifest based on the device's
architecture and OS.

```yaml
Manifests:
  - Name: "linux-amd64"
    Platform:
      architecture: amd64
      os: linux
    Artifacts:
      - URI: s3://bucket/amd64/binary
    Lifecycle:
      Startup:
        Script: "{artifacts:path}/binary"

  - Name: "linux-arm64"
    Platform:
      architecture: arm64
      os: linux
    Artifacts:
      - URI: s3://bucket/arm64/binary
    Lifecycle:
      Startup:
        Script: "{artifacts:path}/binary"
```

## Recipe validation checklist

Before creating a component version, validate:

1. RecipeFormatVersion is `2020-01-25`.
2. ComponentName uses reverse-DNS notation.
3. ComponentVersion is valid semantic versioning.
4. Lifecycle has at least Startup (Install recommended).
5. Artifact URIs are valid S3 paths (`s3://bucket/key`).
6. Configuration keys referenced in lifecycle scripts exist in
   DefaultConfiguration.
7. Platform attributes match target devices.
8. Dependencies list correct version requirements.

## Terraform recipe example

```hcl
resource "aws_greengrass_component_definition" "data_processor" {
  name    = "com.example.DataProcessor"
  version = "2.1.0"

  recipe = templatefile("${path.module}/recipes/data-processor.yaml", {
    artifact_bucket = aws_s3_bucket.artifacts.id
    version         = "2.1.0"
  })

  artifacts {
    uri    = "s3://${aws_s3_bucket.artifacts.id}/artifacts/com.example.DataProcessor/2.1.0/processor.zip"
    unarchive = "ZIP"
  }
}
```

## Step 1 — Component recipe (lifecycle hooks) — moved from SKILL.md

The component recipe is a YAML file that defines the component's
metadata, lifecycle hooks, artifacts, and configuration schema.

**Minimal recipe structure:**

```yaml
---
RecipeFormatVersion: "2020-01-25"
ComponentName: com.example.MyComponent
ComponentVersion: "1.0.0"
ComponentDescription: "My first Greengrass component"
ComponentPublisher: Example
ComponentConfiguration:
  DefaultConfiguration:
    message: "Hello from Greengrass"
    interval: 5
Manifests:
  - Name: "linux-amd64"
    Platform:
      architecture: amd64
      os: linux
    Artifacts:
      - URI: s3://my-bucket/artifacts/my-script.py
        Unarchive: NONE
    Lifecycle:
      Install:
        Script: |
          mkdir -p {artifacts:decompressedPath}/my-component
          cp {artifacts:path}/my-script.py {artifacts:decompressedPath}/my-component/
      Startup:
        Script: |
          python3 {artifacts:decompressedPath}/my-component/my-script.py
      Shutdown:
        Script: |
          echo "Shutting down MyComponent"
```

**Lifecycle hook precedence:**

| Hook | When it runs | Exit code 0 | Exit code non-zero |
|---|---|---|---|
| Install | On first deploy or version update | Component proceeds to Startup | Component deployment fails |
| Startup | After install, on device boot, on restart | Component is RUNNING (stays running) | Component enters ERRORED state; recover hook runs |
| Shutdown | On undeploy, device shutdown, version update | Clean stop | Force kill after timeout |
| Recover | If startup fails (optional) | Component retries startup | Component stays ERRORED |

**Artifact path variables:**

| Variable | Expands to |
|---|---|
| `{artifacts:path}` | Path to the artifact as downloaded (file or directory) |
| `{artifacts:decompressedPath}` | Path to the decompressed artifact (for ZIP/TAR archives) |
| `{work:path}` | Component work directory (persistent, per-component) |
| `{configuration:/<key>}` | Configuration value for the given key |

## Step 2 — Component versioning — moved from SKILL.md

Greengrass v2 components use semantic versioning (`MAJOR.MINOR.PATCH`).
Every recipe change requires a version bump. Creating a component
version with the same version as an existing one is a no-op.

**Version bump rules:**

| Change type | Version bump | Example |
|---|---|---|
| Bug fix, no new features | PATCH | 1.0.0 → 1.0.1 |
| New feature, backward-compatible | MINOR | 1.0.1 → 1.1.0 |
| Breaking change | MAJOR | 1.1.0 → 2.0.0 |
| Recipe lifecycle change | MINOR or MAJOR | 1.1.0 → 1.2.0 |
| Artifact update only | PATCH | 1.1.0 → 1.1.1 |

**Create a component version:**

```bash
# Upload the recipe to S3 (or use inline)
aws greengrassv2 create-component-version \
  --inline-recipe fileb://recipe.yaml \
  --region us-east-1

# Or from S3
aws greengrassv2 create-component-version \
  --lambda-function '{"lambdaArn": "arn:aws:lambda:us-east-1:123456789012:function:my-func:1", "componentName": "com.example.MyLambda", "componentVersion": "1.0.0"}' \
  --region us-east-1
```

**Verify component version created:**

```bash
aws greengrassv2 describe-component \
  --arn "arn:aws:greengrass:us-east-1:123456789012:components:com.example.MyComponent:versions:1.0.0" \
  --region us-east-1
```

## Step 3 — Artifact storage (S3) — moved from SKILL.md

Component artifacts (scripts, binaries, models, archives) are stored
in S3. The recipe references them by S3 URI. Greengrass uses the
token exchange role on the core device to download artifacts (NOT
presigned URLs).

**Upload artifact to S3:**

```bash
aws s3 cp my-script.py s3://my-greengrass-artifacts/artifacts/com.example.MyComponent/1.0.0/my-script.py \
  --region us-east-1
```

**Token exchange role policy (must include s3:GetObject):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::my-greengrass-artifacts/*"
    }
  ]
}
```

**Artifact archive types:**

| Unarchive value | When to use |
|---|---|
| NONE | Single file (script, binary) |
| ZIP | Multiple files compressed as ZIP |
| TAR | Multiple files compressed as TAR |
| TAR_GZ | Multiple files compressed as TAR.GZ |

For ZIP/TAR archives, use `{artifacts:decompressedPath}` in lifecycle
scripts to reference the extracted files.

## Step 4 — Component dependencies (hard vs soft) — moved from SKILL.md

Components can depend on other components. There are two dependency
types:

| Dependency type | Behavior | Use case |
|---|---|---|
| HARD | If dependency fails, THIS component also fails | Required runtime (e.g., aws.lambda for Lambda components) |
| SOFT | If dependency fails, THIS component still starts | Optional features (e.g., a logging component) |

**Recipe with dependencies:**

```yaml
ComponentDependencies:
  - DependencyType: HARD
    ComponentRequire:
      ThingName: aws.lambda
      Version: "2.3.0"
  - DependencyType: SOFT
    ComponentRequire:
      ThingName: com.example.Logging
      Version: "1.0.0"
```

**Dependency resolution order:**

Greengrass resolves dependencies in topological order. HARD
dependencies are installed and started BEFORE the dependent
component. SOFT dependencies are started before but do not block.
