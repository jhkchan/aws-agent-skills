# Diagnostic Commands — Lambda Memory Optimizer

Command listings moved verbatim from SKILL.md: data-gate CLI sources,
SnapStart enablement, /tmp decoupling, and arm64 re-tuning. Load on
demand.

### Pre-flight data gate — required data sources

**Required data sources** (summarized — see reference for full CLI):
1. Function configuration: `aws lambda get-function-configuration`
2. Duration + Invocations (14-30 day window): `aws cloudwatch get-metric-statistics --namespace AWS/Lambda`
3. Memory utilization (Lambda Insights): `aws cloudwatch get-metric-statistics --namespace LambdaInsights --metric-name memory_used`
4. InitDuration (cold start): `aws cloudwatch get-metric-statistics --metric-name InitDuration` (via Logs Insights)
5. CPU utilization: `aws cloudwatch get-metric-statistics --namespace LambdaInsights --metric-name cpu_total_time`
6. Compute Optimizer findings: `aws compute-optimizer get-lambda-function-recommendations`
7. Provisioned concurrency configs: `aws lambda list-provisioned-concurrency-configs`
8. Power Tuning result (if available): `cheapest`, `fastest`, `tested` memory values

### Step 3 — SnapStart enablement (Java-only)

**SnapStart enablement (Java-only):**
```bash
aws lambda update-function-configuration \
  --function-name <name> \
  --snap-start '{"ApplyOn":"PublishedVersions"}'
aws lambda publish-version --function-name <name>
# Point alias at the new version
aws lambda update-alias --function-name <name> \
  --name prod --function-version <new-version>
```

SnapStart snapshots the init-phase memory and restores it in ~200 ms
instead of re-running init. Does NOT change the per-invocation memory
allocation — only the cold-start path. The snapshot is taken AFTER init
completes, so init-time memory spikes are captured in the snapshot.

### Step 5 — decoupling /tmp from memory

**Decoupling /tmp from memory:**
```bash
aws lambda update-function-configuration \
  --function-name <name> \
  --memory-size 256 \
  --ephemeral-storage '{"Size": 2048}'
```

**Cost impact:** Decoupling a function from 2048 MB MemorySize (where
it only needed 256 MB runtime + 1.8 GB /tmp) to 256 MB MemorySize +
2048 MB ephemeral storage saves ~85% on the compute term while
preserving the /tmp capacity.

### Step 6 — mandatory re-tuning after architecture migration

**Mandatory re-tuning after architecture migration:**
```bash
# After migrating to arm64, re-run Power Tuning:
aws stepfunctions start-execution \
  --state-machine-arn <power-tuning-arn> \
  --input '{"lambda":{"resource":"arn:aws:lambda:us-east-1:<acct>:function:<name>","num":5},"power":{"values":[128,256,512,1024,1769,2048,3008]}}'
```
