# Error Handling — ALB Unhealthy Target Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Remediation guidance

### For HEALTH_CHECK_PATH

```bash
aws elbv2 modify-target-group \
  --target-group-arn <tg-arn> \
  --health-check-path <correct-path>
```

Verify the correct path first with a direct curl from within the VPC.

### For PORT_MISMATCH

```bash
# Option 1: Use traffic-port (the target's registered port)
aws elbv2 modify-target-group \
  --target-group-arn <tg-arn> \
  --health-check-port traffic-port

# Option 2: Use a specific port
aws elbv2 modify-target-group \
  --target-group-arn <tg-arn> \
  --health-check-port <port>
```

### For PROTOCOL_MISMATCH

```bash
aws elbv2 modify-target-group \
  --target-group-arn <tg-arn> \
  --health-check-protocol <HTTP|HTTPS>
```

Also update the Matcher if the application returns non-200 codes:

```bash
aws elbv2 modify-target-group \
  --target-group-arn <tg-arn> \
  --matcher HttpCode=200,204
```

### For SG_BLOCKING_HEALTH_CHECK

```bash
aws ec2 authorize-security-group-ingress \
  --group-id <target-sg-id> \
  --ip-permissions \
    IpProtocol=tcp,FromPort=<port>,ToPort=<port>,UserIdGroupPairs=[{GroupId=<alb-sg-id>}]
```

### For DEREGISTRATION_DELAY

```bash
aws elbv2 modify-target-group-attributes \
  --target-group-arn <tg-arn> \
  --attributes Key=deregistration_delay.timeout_seconds,Value=<seconds>
```

Range: 0-3600 seconds. Default: 300.

### For HEALTH_CHECK_THRESHOLD

```bash
aws elbv2 modify-target-group \
  --target-group-arn <tg-arn> \
  --health-check-interval-seconds <30-300> \
  --health-check-timeout-seconds <2-60> \
  --healthy-threshold-count <2-10> \
  --unhealthy-threshold-count <2-10>
```

Typical resilient configuration: interval 30s, timeout 5s, healthy
threshold 3, unhealthy threshold 3.

### For LAMBDA_TARGET_INTEGRATION

- Raise Lambda Timeout if the health check invoke times out.
- Add a fast-path in the handler for health check events.
- Ensure the function returns `statusCode: 200` on health checks.

### For WEIGHTED_ROUTING

```bash
aws elbv2 modify-rule \
  --rule-arn <rule-arn> \
  --actions Type=forward,TargetGroupArn=<tg-arn>,ForwardConfig={TargetGroups=[{TargetGroupArn=<tg-arn-1>,Weight=80},{TargetGroupArn=<tg-arn-2>,Weight=20}]}
```

### For SLOW_START

```bash
aws elbv2 modify-target-group-attributes \
  --target-group-arn <tg-arn> \
  --attributes Key=slow_start.duration_seconds,Value=<0|30-900>
```

Set to 0 to disable slow start. Range when enabled: 30-900 seconds.

### For CROSS_ZONE

```bash
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn <alb-arn> \
  --attributes Key=load_balancing.cross_zone.enabled,Value=true
```
