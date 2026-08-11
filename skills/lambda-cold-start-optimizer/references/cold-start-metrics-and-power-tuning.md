# Cold Start Metrics and Power Tuning Reference

Supplementary reference for the Lambda Cold Start Optimizer skill. Loaded
on-demand when detailed Power Tuning deployment steps, Lambda Insights
metrics, memory-to-CPU mapping, or SnapStart CLI sequences are needed.

## Lambda Insights metrics for cold-start analysis

### Required metrics

| Metric | Namespace | What it measures |
|---|---|---|
| `Duration` | AWS/Lambda | Handler execution time (excludes init) |
| `InitDuration` | AWS/Lambda (reported on cold starts) | Init phase time (includes imports, global-scope code) |
| `Invocations` | AWS/Lambda | Total invocation count |
| `ConcurrentExecutions` | AWS/Lambda | Concurrent execution count at a point in time |
| `Errors` | AWS/Lambda | Invocation errors |
| `Throttles` | AWS/Lambda | Throttled invocations |
| `memory_used` | LambdaInsights | Peak memory per invocation |
| `cpu_total_time` | LambdaInsights | CPU time consumed |
| `coldStarts` | LambdaInsights | Estimated cold-start count |

### Enabling Lambda Insights

```bash
# Enable via CloudWatch console or CLI
aws lambda update-function-configuration \
  --function-name <name> \
  --layers arn:aws:lambda:<region>:580247275435:layer:LambdaInsightsExtension:<version>

# Verify metrics appear after a few invocations
aws cloudwatch get-metric-statistics \
  --namespace LambdaInsights \
  --metric-name memory_used \
  --dimensions Name=function_name,Value=<name> \
  --start-time $(date -d '-1 hour' +%FT%TZ) \
  --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json
```

### Cold-start detection

Lambda reports `InitDuration` only on cold starts (new container
initialization). A cold start occurs when:
- No warm execution environment is available for the function + alias.
- The function has not been invoked recently (container reclaimed).
- A deployment creates new execution environments.

Cold-start frequency estimate:
```
cold_start_rate = cold_starts / total_invocations
```

Typical cold-start rates: 1-5% for steady-traffic functions; 50%+ for
sporadic functions.

## Memory-to-CPU mapping

| Memory (MB) | vCPU (fractional) | Notes |
|---|---|---|
| 128 | ~0.07 vCPU | Minimum; very slow for CPU-bound |
| 256 | ~0.14 vCPU | |
| 512 | ~0.29 vCPU | |
| 1024 | ~0.58 vCPU | |
| 1769 | 1.0 vCPU | Full vCPU threshold |
| 2048 | ~1.16 vCPU | |
| 3072 | ~1.74 vCPU | |
| 3538 | 2.0 vCPU | 2 full vCPUs |
| 5120 | ~2.89 vCPU | |
| 6144 | ~3.47 vCPU | |
| 8192 | ~4.63 vCPU | |
| 10240 (max) | ~5.79 vCPU | Maximum memory |

The CPU-memory ratio is LINEAR. For cold-start optimization, the
inflection point at 1769 MB matters because CPU-bound init code sees
step-function improvement there.

## Power Tuning deployment guide (latency mode)

### Deploy via Serverless Application Repository (SAR)

```bash
# Create the change set (one-time)
aws serverlessrepo create-cloudformation-change-set \
  --application-id arn:aws:serverlessrepo:us-east-1:451482290155:XfE9cVlKBl \
  --stack-name serverlessrepo-lambda-power-tuning \
  --capabilities CAPABILITY_IAM

# Execute the change set
aws cloudformation execute-change-set --change-set-name <ChangeSetId>

# Wait for completion
aws cloudformation wait stack-create-complete \
  --stack-name serverlessrepo-lambda-power-tuning

# Get the state machine ARN
aws cloudformation describe-stacks \
  --stack-name serverlessrepo-lambda-power-tuning \
  --query 'Stacks[0].Outputs[?OutputKey==`powerTuningStateMachineARN`].OutputValue' \
  --output text
```

### Run Power Tuning in latency mode

```bash
aws stepfunctions start-execution \
  --state-machine-arn <state-machine-arn> \
  --input '{
    "lambdaARN": "arn:aws:lambda:us-east-1:<acct>:function:<name>",
    "powerValues": [128, 256, 512, 1024, 2048, 3008],
    "num": 50,
    "payload": {},
    "parallelInvocation": true,
    "strategy": "latency"
  }'
```

Read the `fastest` field from the output (not `cheapest` — that is the
cost-optimization mode). The `fastest` field gives the memory setting
with the lowest average duration.

## SnapStart CLI sequences

### Enable SnapStart (Java only)

```bash
# 1. Enable SnapStart
aws lambda update-function-configuration \
  --function-name <name> \
  --snap-start '{"ApplyOn":"PublishedVersions"}'

# 2. Publish a version (SnapStart snapshots the version)
aws lambda publish-version --function-name <name>

# 3. Create or update an alias
aws lambda update-alias \
  --function-name <name> \
  --name prod \
  --function-version <new-version>

# 4. Verify SnapStart status (wait 1-2 minutes)
aws lambda get-function-configuration \
  --function-name <name> --qualifier <new-version> \
  --query 'SnapStart'
```

### SnapStart eligibility

- Runtime: java21 or later supported Java runtimes (Corretto)
- Package type: Zip only (NOT container images)
- NOT available for: Node.js, Python, Go, Ruby, .NET

### SnapStart caveats

| Issue | Impact | Mitigation |
|---|---|---|
| TCP connections reset | DB/HTTP connections established in init are lost on restore | Re-establish in handler or use lazy-init with validity check |
| Unique values duplicated | Randomness generated in init is identical across restores | Use `SecureRandom` in handler, not init |
| Caching libraries | Caffeine, Guava Cache may behave unexpectedly | Test thoroughly post-enablement |

## ARM64 compatibility matrix

| Runtime | ARM64 support | Notes |
|---|---|---|
| Node.js 18+ | Full | No native deps issues for most packages |
| Python 3.9+ | Full | Pillow, numpy, scipy all have arm64 wheels |
| Java 11+ (Corretto) | Full | Verify JNI/native deps |
| Go 1.x | Full | Recompile with `GOARCH=arm64` |
| .NET 6+ | Full | Verify native interop |
| Ruby 3.x | Full | Verify C extensions |

## Package size thresholds

| Package size | Estimated init overhead | Recommendation |
|---|---|---|
| <5 MB | Negligible (<50 ms) | No action |
| 5-20 MB | Moderate (50-200 ms) | Evaluate dependency trimming |
| 20-50 MB | Significant (200-500 ms) | Trim aggressively, use Proguard (Java) |
| >50 MB | Severe (500+ ms) | Refactor: Proguard, Layers, or container image |

## VPC cold-start diagnostic

```bash
# Check ENI count for Lambda VPC functions
aws ec2 describe-network-interfaces \
  --filters Name=description,Values="AWS Lambda VPC ENI*" \
  --query 'NetworkInterfaces[*].{Id:NetworkInterfaceId,Subnet:SubnetId,Status:Status}' \
  --output table

# Check subnet IP availability
aws ec2 describe-subnets \
  --subnet-ids <subnet-ids> \
  --query 'Subnets[*].{SubnetId:SubnetId,AvailableIPs:AvailableIpAddressCount,CIDR:CidrBlock}' \
  --output table

# Check account ENI limit
aws service-quotas get-service-quota \
  --service-code ec2 \
  --quota-code L-1216C47A \
  --query 'Quota.Value' --output text
```

Since 2019, hyperplane ENIs reduced VPC cold-start overhead to <100 ms.
VPC is no longer a primary cold-start driver. If latency >500 ms,
investigate ENI/subnet/SG issues rather than VPC attachment itself.
