# Runtimes and Architectures Guide — Lambda Layer Deployer

Deep reference on Lambda Layer compatible runtimes, compatible
architectures, zip path conventions per runtime, and the interaction
between the two. Loaded on demand by the skill — kept out of the main
SKILL.md body so the provisioning procedure stays scannable.

## Compatible runtimes

A Lambda Layer declares which runtimes it supports. Lambda enforces
this at attach time — a mismatch causes `ResourceConflictException`.

### Supported runtimes (2025-2026)

| Runtime family | Values | Zip path | Package manager |
|---|---|---|---|
| Python | `python3.10`, `python3.11`, `python3.12`, `python3.13` | `python/` | `pip install -t python/` |
| Node.js | `nodejs18.x`, `nodejs20.x`, `nodejs22.x` | `nodejs/node_modules/` | `npm install --prefix nodejs/` |
| Java | `java17`, `java21` | `java/lib/` | Place jar files |
| Ruby | `ruby3.2`, `ruby3.3`, `ruby3.4` | `ruby/gems/` | `gem install --install-dir ruby/gems/` |
| Provided | `provided.al2`, `provided.al2023` | `bin/`, `lib/` | Custom binaries |

### Multi-runtime layers

A layer can declare multiple compatible runtimes if the content is
generic enough (e.g., shared libraries, config files). However,
runtime-specific package paths must all be present in the zip.

```text
# Example: a layer compatible with both Python and Node.js
python/
  requests/
  boto3/
nodejs/
  node_modules/
    @aws-sdk/
      client-s3/
```

### Runtime deprecation impact

When a runtime is deprecated (e.g., `python3.7`, `nodejs14.x`),
layers declaring ONLY that runtime become unattachable to any
supported function. Always declare the broadest set of currently-
supported runtimes for pure-interpreted dependencies.

### provided.al2 vs provided.al2023

| Property | provided.al2 | provided.al2023 |
|---|---|---|
| Base OS | Amazon Linux 2 | Amazon Linux 2023 |
| glibc | 2.26 | 2.34 |
| Package manager | yum (AL2 repos) | dnf (AL2023 repos) |
| Security model | Long-term support | Rolling updates |

**Compatibility note:** compiled binaries (Go, Rust, C) built for
`provided.al2` may NOT work on `provided.al2023` due to glibc version
differences. Always compile on the target OS or use static linking.

## Compatible architectures

| Architecture | Value | CPU family | Notes |
|---|---|---|---|
| x86_64 | `x86_64` | Intel / AMD | Default; x86_64 instruction set |
| arm64 | `arm64` | AWS Graviton | Up to 34% better price-performance |

### Architecture matching rules

- A function and its layers MUST have matching architectures.
- An `x86_64` layer CANNOT be attached to an `arm64` function.
- An `arm64` layer CANNOT be attached to an `x86_64` function.
- Lambda validates architecture at `update-function-configuration`
  time, not at layer publish time.

### Dual-architecture layers

To support both architectures, publish TWO separate layer versions
(or two separate layers), each with the correct architecture.
Functions then reference the matching layer.

```bash
# Publish x86_64 version
aws lambda publish-layer-version \
  --layer-name my-layer-x86 \
  --zip-file fileb://layer-x86.zip \
  --compatible-runtimes python3.12 \
  --compatible-architectures x86_64

# Publish arm64 version
aws lambda publish-layer-version \
  --layer-name my-layer-arm64 \
  --zip-file fileb://layer-arm64.zip \
  --compatible-runtimes python3.12 \
  --compatible-architectures arm64
```

### Compiled code considerations

For pure-interpreted code (Python source, JavaScript source), the
architecture declaration is enforced by Lambda but the code runs on
either. For compiled code (C extensions, NumPy, SciPy, Go/Rust
binaries), the binary MUST match the target architecture.

| Dependency type | x86_64 layer on arm64 function | arm64 layer on x86_64 function |
|---|---|---|
| Pure Python (`.py`) | Works (but Lambda blocks it) | Works (but Lambda blocks it) |
| C extension (`.so`) | CRASH (illegal instruction) | CRASH (illegal instruction) |
| Go binary | CRASH | CRASH |
| JavaScript (`.js`) | Works (but Lambda blocks it) | Works (but Lambda blocks it) |

**Best practice:** always compile C extensions and binaries on the
target architecture. Use Docker to cross-compile:

```bash
# Build Python layer for arm64 using Docker
docker run --rm --platform linux/arm64 -v "$PWD":/var/task public.ecr.aws/sam/build-python3.12:latest \
  pip install -t layer/python/ cryptography
```

## Zip path conventions (exhaustive reference)

Lambda extracts the layer zip into `/opt`. Each runtime searches
specific paths under `/opt`.

### Python

```text
/opt/python/                    # primary
/opt/python/lib/python3.x/site-packages/  # legacy (also works)

# Lambda adds /opt/python to PYTHONPATH at runtime
# pip install -t python/ <pkg> creates the correct structure
```

### Node.js

```text
/opt/nodejs/node_modules/       # primary

# Lambda adds /opt/nodejs/node_modules to NODE_PATH at runtime
# npm install --prefix nodejs/ <pkg> creates the correct structure
```

### Java

```text
/opt/java/lib/                  # JVM classpath

# Place .jar files in java/lib/
# Lambda adds /opt/java/lib/*.jar to CLASSPATH
```

### Ruby

```text
/opt/ruby/gems/                 # Gem directory
/opt/ruby/lib/                  # Ruby lib directory

# gem install --install-dir ruby/gems/ <gem>
```

### provided.al2 / provided.al2023

```text
/opt/bin/                       # Binaries (added to PATH)
/opt/lib/                       # Libraries (added to LD_LIBRARY_PATH)

# Custom runtime bootstrap can read from any /opt path
```

### Verification: inspect a published layer's content

```bash
# Download the layer zip
aws lambda get-layer-version --layer-name my-layer --version-number 1 \
  --query Content.Location --output text | xargs curl -o layer.zip

# Inspect the zip structure
unzip -l layer.zip | head -20
# Verify the root directory matches the runtime's expected path
```

## Size limits

| Limit | Value |
|---|---|
| Per-layer compressed | 50 MB |
| Function total (all layers + code, uncompressed) | 250 MB |
| Function total (all layers + code, compressed) | 50 MB (for direct upload) |

**Note:** the 250 MB limit is for the UNCOMPRESSED total. A function
with 4 layers at 50 MB compressed each may exceed 250 MB uncompressed.
Monitor total size after layer attachment.

## Common pitfalls

1. **Wrong zip root.** Zipping the outer directory adds a prefix.
   Always `cd` into the directory before `zip -r`.
2. **Missing architecture declaration.** Default is x86_64; arm64
   functions will reject it.
3. **Compiled code on wrong architecture.** Pure-interpreted code
   works on either arch, but C extensions crash if mismatched.
4. **glibc mismatch (AL2 vs AL2023).** Compiled binaries may not be
   portable across the two provided runtimes.
5. **Runtime not declared.** Lambda allows attachment without runtime
   matching, but path resolution is not guaranteed.
