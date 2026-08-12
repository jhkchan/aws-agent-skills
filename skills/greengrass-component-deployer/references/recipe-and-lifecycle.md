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
