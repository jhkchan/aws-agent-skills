# Diagnostic commands — lambda-timeout-troubleshooter

Pre-flight and per-step probe commands, moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Pre-flight commands (moved from SKILL.md)

```bash
# 1. Function configuration
aws lambda get-function-configuration \
  --function-name <name-or-arn> --qualifier <alias-or-version> --output json

# 2. Duration and InitDuration metrics
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=<name> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 60 --statistics Average,p99,p99.9,Maximum --output json

aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name MemoryUtilization \
  --dimensions Name=FunctionName,Value=<name> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json

# 3. Recent timeouts with surrounding context
aws logs filter-log-events \
  --log-group-name /aws/lambda/<name> \
  --start-time $(date -d '-30 minutes' +%s)000 \
  --filter-pattern '"Task timed out"' --output json

# 4. X-Ray trace for the slowest invocations
aws xray get-trace-summaries \
  --service-name <name> --start-time $(date -d '-30 minutes' +%s) \
  --end-time $(date +%s) --response-time --output json
```

## Step 2 probe commands — TIMEOUT_CONFIG vs TIMEOUT_DOWNSTREAM (moved from SKILL.md)

```bash
aws lambda get-function-configuration --function-name <name> --output json | \
  jq '{Timeout, MemorySize, Runtime}'
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=<name> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 60 --statistics p99,p99.9,Maximum --output json
```

## Step 3 probe commands — TIMEOUT_INIT_PHASE (moved from SKILL.md)

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/<name> \
  --filter-pattern '"Init Duration"' \
  --start-time $(date -d '-1 hour' +%s)000 --output json

aws lambda get-function-configuration --function-name <name> --output json | \
  jq '{SnapStart: .SnapStart, Runtime, MemorySize}'
```

## Step 4 probe commands — TIMEOUT_SDK_RETRY_STORM (moved from SKILL.md)

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/<name> \
  --start-time $(date -d '-1 hour' +%s)000 \
  --filter-pattern '"Retrying request"' --output json
```

## Step 6 probe commands — TIMEOUT_DB_CONNECTION (moved from SKILL.md)

```bash
aws rds describe-db-proxies --output json
```

## Step 7 probe commands — TIMEOUT_STEP_FUNCTIONS_MISMATCH (moved from SKILL.md)

```bash
aws stepfunctions describe-state-machine \
  --state-machine-arn <arn> --output json | jq '.definition'
```

## Step 9 probe commands — TIMEOUT_PROV_CONCURRENCY_INIT (moved from SKILL.md)

```bash
aws lambda list-provisioned-concurrency-configs \
  --function-name <name> --output json

aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name ProvisionedConcurrencySpilloverInvocations \
  --dimensions Name=FunctionName,Value=<name>,Name=Resource,Value=<alias> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum --output json
```

## Step 10 probe commands — TIMEOUT_OOM_BEFORE_TIMEOUT (moved from SKILL.md)

```bash
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name MemoryUtilization \
  --dimensions Name=FunctionName,Value=<name> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Maximum --output json
```
