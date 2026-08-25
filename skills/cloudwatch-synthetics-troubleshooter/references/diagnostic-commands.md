# Diagnostic Commands (load on demand) — CloudWatch Synthetics Troubleshooter

Pre-flight and diagnostic command listings moved verbatim from SKILL.md. Load on demand.

---

## Step 2 — TIMEOUT probes (moved from SKILL.md)

```bash
# Canary config including timeout.
aws synthetics describe-canary --name <canary> \
  --query 'Canary.{type:Type,runtime:RuntimeVersion,timeout:RunConfig.TimeoutInSeconds,schedule:Schedule.Expression}'

# Last 5 runs with duration and status.
aws synthetics get-canary-runs --name <canary> --max-results 5 \
  --query 'CanaryRuns[*].{status:Status,state:State,duration:Timing.Duration}'

# Duration metric trend.
aws cloudwatch get-metric-statistics --namespace CloudWatchSynthetics \
  --metric-name Duration --dimensions Name=CanaryName,Value=<canary> \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Average Maximum --output json
```

## Step 3 — AUTH_FAILURE probes (moved from SKILL.md)

```bash
# Check canary log for auth errors.
aws logs start-query --log-group-name /aws/lambda/cwsyn-<canary-name> \
  --start-time $(date -u -v-1H +%s) --end-time $(date -u +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /40[13]/ or @message like /Unauthorized/ or @message like /token/ | sort @timestamp desc | limit 20'

# Check Secrets Manager rotation history.
aws secretsmanager describe-secret --secret-id <secret-id> \
  --query '{name:Name,rotated:LastRotatedDate,changed:LastChangedDate}'

# Simulate canary role's secret access.
aws iam simulate-principal-policy --policy-source-arn <canary-role-arn> \
  --action-names secretsmanager:GetSecretValue \
  --resource-arns arn:aws:secretsmanager:<region>:<account>:secret:<secret-id>
```

## Step 4 — VISUAL_MONITORING_MISMATCH probes (moved from SKILL.md)

```bash
# Visual Monitoring configuration.
aws synthetics describe-canary --name <canary> --query 'Canary.RunConfig'

# List artifacts for the failed run.
aws s3 ls s3://<artifact-bucket>/canary/<canary-name>/<run-id>/ --recursive --human-readable

# Download screenshots for comparison.
aws s3 cp s3://<artifact-bucket>/canary/<canary-name>/<run-id>/screenshots/ /tmp/canary-screenshots/ --recursive
```

## Step 5 — RUNTIME_EXCEPTION probes (moved from SKILL.md)

```bash
# Query canary log for errors and stack traces.
aws logs start-query --log-group-name /aws/lambda/cwsyn-<canary-name> \
  --start-time $(date -u -v-1H +%s) --end-time $(date -u +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /Error/ or @message like /Exception/ or @message like /TypeError/ | sort @timestamp desc | limit 30'

# Check runtime version.
aws synthetics describe-canary --name <canary> --query 'Canary.RuntimeVersion'

# List available runtime versions.
aws synthetics describe-runtime-versions --max-results 10 \
  --query 'RuntimeVersionList[*].{version:VersionName,deprecation:DeprecationDate}'
```

## Step 6 — TARGET_ENDPOINT_DOWN probes (moved from SKILL.md)

```bash
# Independent endpoint check.
curl -sI -o /dev/null -w "%{http_code} %{time_total}s\n" https://<target-url>

# Route 53 DNS answer.
aws route53 test-dns-answer --hosted-zone-id <zone-id> --record-name <record> --record-type A

# ALB target health.
aws elbv2 describe-target-health --target-group-arn <tg-arn> \
  --query 'TargetHealthDescriptions[*].{target:Target.Id,health:TargetHealth.State,reason:TargetHealth.Reason}'

# SuccessPercent trend — sustained 0% confirms target down.
aws cloudwatch get-metric-statistics --namespace CloudWatchSynthetics \
  --metric-name SuccessPercent --dimensions Name=CanaryName,Value=<canary> \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Average --output json
```

## Step 7 — ARTIFACT_MISMATCH / INSUFFICIENT_PERMISSIONS probes (moved from SKILL.md)

```bash
# Canaries execution role and artifact location.
aws synthetics describe-canary --name <canary> \
  --query 'Canary.{role:ExecutionRoleArn,artifact:ArtifactS3Location,code:Code.Location}'

# Simulate canary role permissions.
aws iam simulate-principal-policy --policy-source-arn <canary-role-arn> \
  --action-names s3:GetObject s3:ListBucket logs:CreateLogStream \
  --resource-arns arn:aws:s3:::<artifact-bucket> arn:aws:s3:::<artifact-bucket>/*

# Verify artifact zip exists.
aws s3 ls s3://<artifact-bucket>/canary/<canary-name>/
```

## Step 8 — RATE_LIMITED / NETWORK_ERROR / DNS_FAILURE probes (moved from SKILL.md)

```bash
# Check canary logs for network errors.
aws logs start-query --log-group-name /aws/lambda/cwsyn-<canary-name> \
  --start-time $(date -u -v-1H +%s) --end-time $(date -u +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /ECONNREFUSED/ or @message like /ENOTFOUND/ or @message like /429/ | sort @timestamp desc | limit 20'

# VPC config for VPC canaries.
aws synthetics describe-canary --name <canary> --query 'Canary.VpcConfig'
```

## Diagnostic command reference (numbered 1-8) (moved from SKILL.md)

```bash
# 1. List all canaries with current state.
aws synthetics describe-canaries \
  --query 'Canaries[*].{name:Name,state:State,type:Type}' --output table

# 2. Canary configuration.
aws synthetics describe-canary --name <canary> \
  --query 'Canary.{name:Name,state:State,type:Type,runtime:RuntimeVersion,role:ExecutionRoleArn,timeout:RunConfig.TimeoutInSeconds,schedule:Schedule.Expression,vpc:VpcConfig,artifact:ArtifactS3Location}'

# 3. Recent runs with status and timing.
aws synthetics get-canary-runs --name <canary> --max-results 10 \
  --query 'CanaryRuns[*].{status:Status,state:State,duration:Timing.Duration,start:Timing.Started}'

# 4. SuccessPercent metric.
aws cloudwatch get-metric-statistics --namespace CloudWatchSynthetics \
  --metric-name SuccessPercent --dimensions Name=CanaryName,Value=<canary> \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Average --output json

# 5. Canary log query for errors.
aws logs start-query --log-group-name /aws/lambda/cwsyn-<canary-name> \
  --start-time $(date -u -v-1H +%s) --end-time $(date -u +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /Error/ or @message like /Exception/ | sort @timestamp desc | limit 30'

# 6. List canary artifacts (screenshots, HAR).
aws s3 ls s3://<artifact-bucket>/canary/<canary-name>/ --recursive --human-readable

# 7. Trigger a manual canary run.
aws synthetics start-canary --name <canary>

# 8. IAM permission simulation.
aws iam simulate-principal-policy --policy-source-arn <canary-role-arn> \
  --action-names s3:GetObject logs:CreateLogStream secretsmanager:GetSecretValue \
  --resource-arns arn:aws:s3:::<bucket> arn:aws:s3:::<bucket>/* "*"
```

