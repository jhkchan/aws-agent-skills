# Diagnostic Commands — ALB 5xx Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Account-wide pre-flight commands

```bash
# 1. Load balancer configuration (type, scheme, state, subnets, SGs)
aws elbv2 describe-load-balancers --load-balancer-arns <arn> --output json

# 2. Listeners (protocols, SSL policies, default actions, certificates)
aws elbv2 describe-listeners --load-balancer-arn <arn> --output json

# 3. Listener rules (priorities, conditions, actions — the routing logic)
aws elbv2 describe-rules --listener-arn <listener-arn> --output json

# 4. Target groups (health check config, target type, port, protocol)
aws elbv2 describe-target-groups --load-balancer-arn <arn> --output json

# 5. Target health (the single highest-signal command)
aws elbv2 describe-target-health --target-group-arn <tg-arn> --output json

# 6. Load balancer attributes (idle timeout, deregistration delay, access logs)
aws elbv2 describe-load-balancer-attributes --load-balancer-arn <arn> --output json

# 7. Security groups on the ALB
aws ec2 describe-security-groups \
  --group-ids $(aws elbv2 describe-load-balancers \
    --load-balancer-arns <arn> --output json | \
    jq -r '.LoadBalancers[0].SecurityGroups[]') --output json

# 8. CloudWatch metrics — HTTPCode_Target_5XX_Count, TargetResponseTime
aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB \
  --metric-name HTTPCode_Target_5XX_Count \
  --dimensions Name=LoadBalancer,Value=<arn-suffix> Name=TargetGroup,Value=<tg-suffix> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Sum --output json

# 9. AWS Health (regional events for ELB)
aws health describe-events --filter services=ELASTICLOADBALANCING,\
  eventStatusCodes=OPEN,UPCOMING --region us-east-1 --output json
```

## Step 1b: Gather access logs (when the code is ambiguous)

If the operator reports "we're getting 5xx" without a specific code, or
the code varies request-to-request, fetch access logs first.

**ALB access log location:** S3 bucket configured in
`describe-load-balancer-attributes` under `access_logs.s3.bucket`.

```bash
# List recent access log objects
aws s3 ls s3://<bucket>/<prefix>/AWSLogs/<account>/elasticloadbalancing/<region>/ \
  --recursive | sort | tail -20

# Download and analyze recent logs (filter for 5xx)
aws s3 cp s3://<bucket>/<prefix>/AWSLogs/<account>/elasticloadbalancing/<region>/ \
  /tmp/alb-logs/ --recursive
# Parse for 5xx responses
awk '$14 >= 500' /tmp/alb-logs/*.log.gz | zcat | head -50
```

**ALB access log format (space-delimited, key fields):**
```
time elb client:port target:port request_time target_processing_time
response_time elb_status_code target_status_code received_bytes
sent_bytes request "user_agent" ssl_cipher ssl_protocol
target_group_arn trace_id domain_name chosen_cert_arn ...
error_reason
```

The `target_processing_time`, `target_status_code`, and `error_reason`
fields are the highest-signal for 5xx diagnosis.

## Step 2a probes: 502 — target returned invalid HTTP or connection failed

```bash
# Target health (are the targets even healthy?)
aws elbv2 describe-target-health --target-group-arn <tg-arn> --output json

# If targets are healthy, test the target directly (bypassing the ALB)
# For instance-type targets:
aws ec2 describe-instances --instance-ids <i-id> --output json | \
  jq '.Reservations[0].Instances[0].PrivateIpAddress'
ssh <bastion> "curl -v http://<target-private-ip>:<target-port>/"

# Check ALB access logs for error_reason
aws s3 ls s3://<bucket>/<prefix>/... --recursive | tail -5
# Download and grep for error_reason on 502 responses
```

## Step 2b probes: 502 — target SG does not allow ALB SG

```bash
# Fetch the target's security group (for instance-type targets)
aws ec2 describe-instances --instance-ids <i-id> --output json | \
  jq '.Reservations[0].Instances[0].SecurityGroups[].GroupId'

# For each target SG, check inbound rules on the target port
aws ec2 describe-security-groups --group-ids <sg-target> --output json | \
  jq '.SecurityGroups[].IpPermissions[]'

# Fetch the ALB's security group
aws elbv2 describe-load-balancers --load-balancer-arns <arn> --output json | \
  jq -r '.LoadBalancers[0].SecurityGroups[]'
```

## Step 3a probes: 503 — all targets unhealthy (health check failing)

```bash
# Target health (the smoking gun)
aws elbv2 describe-target-health --target-group-arn <tg-arn> --output json
# Look for: State: unhealthy, Reason: Target.FailedHealthChecks

# Target group health check configuration
aws elbv2 describe-target-groups --target-group-arns <tg-arn> --output json | \
  jq '.TargetGroups[0].HealthCheckConfig'
# Key fields: HealthCheckPath, HealthCheckPort, HealthCheckProtocol,
#   Matcher.HttpCode, HealthCheckIntervalSeconds, HealthCheckTimeoutSeconds,
#   HealthyThresholdCount, UnhealthyThresholdCount

# Test the health check endpoint directly on a target
ssh <bastion> "curl -v http://<target-ip>:<target-port><health-check-path>"
```

## Step 3b probes: 503 — zero registered targets

```bash
# Target group configuration
aws elbv2 describe-target-groups --target-group-arns <tg-arn> --output json | \
  jq '.TargetGroups[0] | {TargetType, Port, Protocol}'

# Registered targets
aws elbv2 describe-target-health --target-group-arn <tg-arn> --output json | \
  jq '.TargetHealthDescriptions'
```

## Step 3c probes: 503 — all targets draining

```bash
# Target health
aws elbv2 describe-target-health --target-group-arn <tg-arn> --output json
# Look for: State: draining

# Deregistration delay
aws elbv2 describe-target-group-attributes --target-group-arn <tg-arn> --output json | \
  jq '.Attributes[] | select(.Key == "deregistration_delay.timeout_seconds")'
```

## Step 4 probes: 504 — target did not respond in time

```bash
# ALB idle timeout
aws elbv2 describe-load-balancer-attributes --load-balancer-arn <arn> --output json | \
  jq '.Attributes[] | select(.Key == "idle_timeout.timeout_seconds")'

# Target response time (from ALB access logs)
# Download logs and check target_processing_time
# Values approaching the idle timeout indicate a slow target

# CloudWatch TargetResponseTime metric
aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --dimensions Name=LoadBalancer,Value=<arn-suffix> Name=TargetGroup,Value=<tg-suffix> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json

# Test the target directly (bypassing the ALB)
ssh <bastion> "time curl -v http://<target-ip>:<target-port>/"
```

## Step 5 probes: 561 — WAF blocked the request

```bash
# Check WAF Web ACLs associated with the ALB
aws wafv2 get-web-acl-for-resource --resource-arn <alb-arn> --output json

# Or list Web ACLs in the region
aws wafv2 list-web-acls --scope REGIONAL --output json

# Fetch WAF logs (if logged to CloudWatch or S3)
aws logs filter-log-events \
  --log-group-name aws-waf-logs-<acl-name> \
  --filter-pattern '"action":"BLOCK"' \
  --start-time $(date -u -d '-1 hour' +%s)000 \
  --output json | jq '.events[].message'
```

## Step 6 probes: listener rule misconfiguration

```bash
# Listener rules (priority order matters!)
aws elbv2 describe-rules --listener-arn <listener-arn> --output json | \
  jq '.Rules[] | {Priority, Conditions, Actions}'

# Default action on the listener
aws elbv2 describe-listeners --listener-arns <listener-arn> --output json | \
  jq '.Listeners[0].DefaultActions'
```

## Step 7 probes: 500 — rare ALB internal failure

```bash
# Check AWS Health Dashboard for ELB events
aws health describe-events \
  --filter services=ELASTICLOADBALANCING,eventStatusCodes=OPEN,UPCOMING \
  --region us-east-1 --output json
```
