# Diagnostic Commands — Global Accelerator Endpoint Deployer

Diagnostic, observability, and pre-flight command listings moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Step 8 — Flow logs and CloudWatch metrics (moved from SKILL.md)

### Flow logs

Global Accelerator supports flow logs for traffic analysis. Flow logs
can be sent to CloudWatch Logs or Amazon S3.

```bash
aws globalaccelerator update-accelerator \
  --accelerator-arn "$ACCEL_ARN" \
  --flow-log-cloudwatch-log-group-arn arn:aws:logs:us-west-2:123456789012:log-group:/aws/globalaccelerator/my-accelerator
```

### CloudWatch metrics

Key metrics: NewFlowCount, FlowCountInActive, ProcessedBytesIn,
ProcessedBytesOut, HealthyEndpointCount, UnhealthyEndpointCount.

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/GlobalAccelerator \
  --metric-name HealthyEndpointCount \
  --dimensions Name=EndpointGroup,Value="$EG_PRIMARY" \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 --statistics Average
```

