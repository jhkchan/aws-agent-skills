# Diagnostic and verification commands — lambda-function-url-deployer

> Content moved verbatim from SKILL.md during progressive-disclosure
> restructuring. Load on demand.

## Verify function URL creation (moved from SKILL.md Step 1)

**Verify the function URL was created:**

```bash
aws lambda get-function-url-config \
  --function-name my-function \
  --region us-east-1
```

## Verify function timeout vs 15s cap (moved from SKILL.md Step 5)

**Verify the function's configured timeout:**

```bash
aws lambda get-function-configuration \
  --function-name my-function \
  --query 'Timeout' \
  --region us-east-1
```

## Verify function URL qualifier (moved from SKILL.md Step 7)

**Verify the qualifier:**

```bash
aws lambda get-function-url-config \
  --function-name my-function \
  --qualifier prod \
  --region us-east-1
```

## Step 8 detail: CloudWatch metrics and alarm CLI (moved from SKILL.md)

**Monitor function URL metrics via CLI:**

```bash
# Get UrlRequests for the last hour
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name UrlRequests \
  --dimensions Name=FunctionName,Value=my-function \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region us-east-1

# Get Url5xx errors
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Url5xx \
  --dimensions Name=FunctionName,Value=my-function \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region us-east-1
```

**Set up alarms for 5xx errors:**

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "lambda-url-5xx-my-function" \
  --metric-name Url5xx \
  --namespace AWS/Lambda \
  --dimensions Name=FunctionName,Value=my-function \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --period 300 \
  --evaluation-periods 1 \
  --statistic Sum \
  --region us-east-1
```

