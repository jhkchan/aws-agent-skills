# Lambda Memory and Power Tuning Reference

Supplementary reference for the Lambda Memory Optimizer skill. Loaded
on-demand when detailed pricing math, Power Tuning deployment steps,
memory-to-CPU mapping, ARM64 ratio comparison, EFS/container/Layers
overhead baselines, or ephemeral storage pricing are needed.

## Lambda pricing (us-east-1, 2026, USD)

### Request pricing

| Pricing model | $/request | Notes |
|---|---|---|
| On-demand | $0.0000002 (0.00002 cents) | First 1M requests/month free tier |
| Provisioned concurrency requests | $0.00005 | Charged IN ADDITION to provisioned compute; 250x more expensive than on-demand per request |

### Compute pricing ($/GB-second)

| Pricing model | $/GB-second | Idle charge? | Notes |
|---|---|---|---|
| On-demand | $0.0000166667 | No | Pay only for execution time |
| Provisioned concurrency | $0.000015 | YES — bills for full provisioned window | Slightly cheaper per GB-second but pays for idle |

### Ephemeral storage pricing

| Dimension | Rate | Notes |
|---|---|---|
| /tmp storage | $0.0000000625/MB-second | Decoupled from MemorySize since 2022; up to 10 GB |

### Free tier

- 1,000,000 requests/month free (on-demand only)
- 400,000 GB-seconds/month free (on-demand only)
- Provisioned concurrency is NOT included in the free tier

### Duration billing precision

Lambda bills duration in 1 ms increments (since 2021). Previously
billed in 100 ms increments — the change made sub-100ms functions
significantly cheaper. Always report duration in milliseconds.

## Memory-to-CPU mapping (x86_64)

| Memory (MB) | vCPU (fractional) | Notes |
|---|---|---|
| 128 | ~0.07 vCPU | Minimum; very slow for CPU-bound workloads |
| 256 | ~0.14 vCPU | |
| 512 | ~0.29 vCPU | |
| 1024 | ~0.58 vCPU | |
| 1769 | 1.0 vCPU | Full vCPU threshold (x86_64) |
| 2048 | ~1.16 vCPU | |
| 3072 | ~1.74 vCPU | |
| 3538 | 2.0 vCPU | 2 full vCPUs |
| 5120 | ~2.89 vCPU | |
| 6144 | ~3.47 vCPU | |
| 8192 | ~4.63 vCPU | |
| 10240 (max) | 10 GB | ~5.79 vCPU |

The CPU-memory ratio is LINEAR on x86_64. The inflection point at
1769 MB matters because Lambda's scheduler allocates full vCPU slices
at that boundary — CPU-bound workloads see step-function improvements
there.

## Memory-to-CPU mapping (arm64 / Graviton2)

ARM64 (Graviton2) has a different memory-to-vCPU curve. The same
memory allocation yields a different vCPU slice on arm64 than x86_64.
Key differences:

- **Graviton2 cores are ~20% faster per vCPU** for many workloads
  (especially compute-intensive: crypto, compression, image processing).
- **The U-curve minimum may be at a LOWER memory setting on arm64**
  than x86_64 for the same workload, because each vCPU slice does more
  work per unit time.
- **The 1-vCPU threshold on arm64 is at a different memory value**
  than 1769 MB (the x86_64 threshold). Power Tuning measures the
  actual threshold empirically.
- **Always re-run Power Tuning after architecture migration.** The
  U-curve shifts; the previous x86_64 optimum is stale on arm64.

**ARM64 vs x86_64 U-curve comparison (example workload):**
```
x86_64:  Cheapest at 1024 MB (~0.58 vCPU), 950 ms, $0.0000158/invocation
arm64:   Cheapest at 768 MB (Graviton2), 880 ms, $0.0000099/invocation
         Saving: 37% cheaper AND 7% faster at LOWER memory on arm64
```

## Power Tuning deployment guide

### Deploy via Serverless Application Repository (SAR)

```bash
# Create the change set (one-time)
aws serverlessrepo create-cloudformation-change-set \
  --application-id arn:aws:serverlessrepo:us-east-1:451482290155:XfE9cVlKBl \
  --stack-name serverlessrepo-lambda-power-tuning \
  --capabilities CAPABILITY_IAM

# Note the ChangeSetId from the response, then execute:
aws cloudformation execute-change-set \
  --change-set-name <ChangeSetId>

# Wait for completion
aws cloudformation wait stack-create-complete \
  --stack-name serverlessrepo-lambda-power-tuning

# Get the state machine ARN
aws cloudformation describe-stacks \
  --stack-name serverlessrepo-lambda-power-tuning \
  --query 'Stacks[0].Outputs[?OutputKey==`powerTuningStateMachineARN`].OutputValue' \
  --output text
```

### Power Tuning input schema

```json
{
  "lambda": {
    "resource": "arn:aws:lambda:us-east-1:<acct>:function:<name>",
    "payload": {},
    "num": 50,
    "enabled": true,
    "parallelInvocation": true
  },
  "power": {
    "values": [128, 256, 512, 1024, 1769, 2048, 3008],
    "payload": {},
    "num": 5,
    "parallelInvocation": false
  }
}
```

### Reading Power Tuning output

The State Machine output includes:
- **`cheapest`**: the memory value with the lowest cost per invocation.
- **`fastest`**: the memory value with the lowest duration.
- **`stable`**: the memory value with the lowest duration variance.
- **`costWeighted`**: weighted cost (for custom optimization strategies).
- **Visualization URL**: https://lambda-power-tuning.show/#<hash> —
  shows the U-curve graphically.

Always surface BOTH `cheapest` and `fastest` in the recommendation.
The operator chooses based on whether the priority is FinOps (cost) or
UX (latency). The two may differ significantly.

## EFS memory overhead baseline

| EFS configuration | Resident memory baseline | Notes |
|---|---|---|
| No EFS mount | 0 MB | Default |
| EFS mount, no I/O | ~64 MB | EFS client allocates buffers at init |
| EFS mount, active I/O | ~64-128 MB | Buffer cache scales with I/O volume |
| EFS mount, large file reads | ~128-256 MB | Can spike higher for sequential reads |

Recommendation: If EFS is used for infrequent large-file access, add
128 MB to the minimum viable MemorySize. If EFS is used for frequent
small-file access, consider S3 pre-signed URLs instead (no resident
memory overhead).

## Container image memory overhead

| Container image size | Cold-start memory overhead | Notes |
|---|---|---|
| < 50 MB (distroless / alpine) | ~32 MB | Minimal overhead |
| 50-250 MB (slim base) | ~64 MB | Typical Python/Node slim image |
| 250 MB-1 GB (full base) | ~128 MB | ubuntu:latest, amazonlinux:2 |
| > 1 GB (heavy image) | ~256 MB+ | Not recommended; use multi-stage builds |

Minimum recommended MemorySize for container-image functions: 256 MB
(to accommodate cold-start image extraction + init + handler).

Optimization tips:
- Use multi-stage builds to strip build tools from the runtime image.
- Use distroless or alpine base images.
- Remove build dependencies (gcc, make, -dev packages) after install.
- Use `pip install --no-cache-dir` to reduce image layer size.

## Lambda Layers memory impact

| Layer count | Init-time overhead | Notes |
|---|---|---|
| 0-2 layers | < 50 ms | Negligible |
| 3-4 layers | 50-150 ms | Measurable but acceptable |
| 5+ layers | 150-500 ms+ | Each layer is a separate zip extraction |

Recommendation: Consolidate layers. Move shared code to a runtime
package manager (pip, npm) instead of layers where possible. Layers
are best for:
- Lambda Extensions (observability, security)
- Runtime-specific binaries (e.g., ffmpeg, ImageMagick)
- Shared corporate libraries (when centralization matters more than
  init speed)

## SnapStart runtime support matrix

| Runtime | SnapStart support | Notes |
|---|---|---|
| Java 11 (Corretto) | GA (2023) | Original launch runtime |
| Java 17 (Corretto) | GA (2023) | |
| Java 21 (Corretto) | GA (2024) | |
| Python | Not supported | Use lazy init + connection reuse instead |
| Node.js | Not supported | Use lazy init + connection reuse instead |
| .NET | Not supported | |
| Go | Not supported | Go has fast init already (~50 ms) |
| Ruby | Not supported | |

SnapStart snapshots the init-phase memory and restores it in ~200 ms.
Does NOT change the per-invocation memory allocation. The snapshot is
taken AFTER init completes.

## Ephemeral storage (/tmp) configuration

```bash
# Allocate 2 GB of /tmp storage (independent of MemorySize)
aws lambda update-function-configuration \
  --function-name <name> \
  --ephemeral-storage '{"Size": 2048}'

# Query current ephemeral storage
aws lambda get-function-configuration \
  --function-name <name> \
  --query 'EphemeralStorage.Size'
```

Pricing: $0.0000000625/MB-second. At 2 GB allocated, the storage cost
is ~$0.13/month (negligible compared to compute). The main benefit is
decoupling /tmp from MemorySize, so the function can have low runtime
memory AND large /tmp without paying for unnecessary compute.

## Regional pricing multipliers (representative)

| Region | Multiplier vs us-east-1 | Notes |
|---|---|---|
| us-east-1 | 1.00 | Baseline |
| us-west-2 | 1.00 | Same pricing tier |
| eu-west-1 | 1.10 | Slight uplift |
| ap-south-1 | 1.05 | Mumbai |
| ap-southeast-2 | 1.15 | Sydney |
| sa-east-1 | 1.20 | Sao Paulo (highest) |

For multi-region deployments, re-state pricing per region.

## Cost calculation worked example

```
Inputs:
  Function: image-enrichment-prod
  Runtime: python3.12
  MemorySize: 128 MB (current)
  Power Tuning cheapest: 512 MB at 950 ms
  Invocations: 47M/month
  Architecture: x86_64 (current) → arm64 (proposed)
  Region: us-east-1
  PC: none

Current monthly cost:
  Compute: 47,000,000 × 5.0 × (128/1024=0.125) × $0.0000166667 = $489.58
  Requests: 47,000,000 × $0.0000002 = $9.40
  Total: $498.98/month

Projected monthly cost (512 MB + arm64):
  Compute: 47,000,000 × 0.95 × (512/1024=0.5) × $0.0000166667 × 0.80 (ARM)
         = 47M × 0.95 × 0.5 × $0.0000166667 × 0.80
         = $297.67
  Requests: 47,000,000 × $0.0000002 = $9.40
  Total: $307.07/month

Monthly saving: $191.91 (38.5%)
Annual saving: $2,302.92

Latency improvement: p95 6200 ms → ~1100 ms (82% reduction)
```

## AWS documentation

- Lambda pricing — https://aws.amazon.com/lambda/pricing/
- Lambda memory and CPU — https://docs.aws.amazon.com/lambda/latest/dg/configuration-memory.html
- Lambda SnapStart — https://docs.aws.amazon.com/lambda/latest/dg/configuration-snapstart.html
- Lambda ephemeral storage — https://docs.aws.amazon.com/lambda/latest/dg/configuration-ephemeral-storage.html
- AWS Lambda Power Tuning — https://github.com/alexcasalboni/aws-lambda-power-tuning
- CloudWatch Lambda Insights — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Lambda-Insights.html
