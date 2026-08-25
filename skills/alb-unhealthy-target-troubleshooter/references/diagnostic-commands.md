# ALB Health Check Diagnostic Commands Reference

Supplementary reference for the ALB Unhealthy Target Troubleshooter skill.
A curated command catalog for each diagnostic layer, mapped to the
decision tree in SKILL.md.

## Layer 1: Target health overview

```bash
# All targets with their health state and reason
aws elbv2 describe-target-health \
  --target-group-arn <tg-arn> --output json | \
  jq '.TargetHealthDescriptions[] | {
    Target: .Target.Id,
    Port: .Target.Port,
    AZ: .Target.AvailabilityZone,
    State: .TargetHealth.State,
    Reason: .TargetHealth.Reason,
    Description: .TargetHealth.Description
  }'

# Target group configuration
aws elbv2 describe-target-groups \
  --target-group-arns <tg-arn> --output json | \
  jq '.TargetGroups[] | {
    HealthCheckPath, HealthCheckPort, HealthCheckProtocol,
    HealthCheckTimeoutSeconds, HealthCheckIntervalSeconds,
    HealthyThresholdCount, UnhealthyThresholdCount,
    Matcher, Protocol, Port, TargetType, VpcId
  }'

# Target group attributes
aws elbv2 describe-target-group-attributes \
  --target-group-arn <tg-arn> --output json | \
  jq '.Attributes'
```

## Layer 2: Security group verification

```bash
# Target security group ingress rules
aws ec2 describe-security-groups \
  --group-ids <target-sg-id> --output json | \
  jq '.SecurityGroups[].IpPermissions[] | {
    Protocol: .IpProtocol,
    FromPort, ToPort,
    Sources: [.UserIdGroupPairs[].GroupId,
              .IpRanges[].CidrIp,
              .Ipv6Ranges[].CidrIpv6]
  }'

# ALB security group and subnets
aws elbv2 describe-load-balancers \
  --load-balancer-arns <alb-arn> --output json | \
  jq '.LoadBalancers[] | {
    SGs: .SecurityGroups,
    AZs: [.AvailabilityZones[] | {ZoneName, SubnetId, LoadBalancerAddresses}],
    VpcId
  }'

# ALB ENI private IPs (health checker source IPs)
aws ec2 describe-network-interfaces \
  --filters Name=description,Values="ELB app/<alb-name>/*" \
  --output json | \
  jq '.NetworkInterfaces[] | {
    PrivateIp: .PrivateIpAddress,
    SubnetId: .SubnetId,
    AZ: .AvailabilityZone
  }'

# Verify connectivity from ALB subnet to target
# Run from an EC2 instance in the ALB subnet:
curl -v --connect-timeout 5 \
  http://<target-private-ip>:<health-check-port><health-check-path>
```

## Layer 3: CloudWatch metrics

```bash
# UnHealthyHostCount per target group + AZ
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name UnHealthyHostCount \
  --dimensions Name=TargetGroup,Value=<tg-id> \
    Name=LoadBalancer,Value=<alb-id> \
    Name=AvailabilityZone,Value=<az> \
  --start-time $(date -d '-1 hour' +%FT%TZ) \
  --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum,Maximum --output json

# HealthyHostCount per target group + AZ
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name HealthyHostCount \
  --dimensions Name=TargetGroup,Value=<tg-id> \
    Name=LoadBalancer,Value=<alb-id> \
  --start-time $(date -d '-1 hour' +%FT%TZ) \
  --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Minimum --output json

# TargetConnectionErrorCount (connection failures from ALB to target)
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name TargetConnectionErrorCount \
  --dimensions Name=TargetGroup,Value=<tg-id> \
    Name=LoadBalancer,Value=<alb-id> \
  --start-time $(date -d '-1 hour' +%FT%TZ) \
  --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum --output json

# HTTPCode_Target_5XX (target-side 5xx responses)
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name HTTPCode_Target_5XX_Count \
  --dimensions Name=TargetGroup,Value=<tg-id> \
    Name=LoadBalancer,Value=<alb-id> \
  --start-time $(date -d '-1 hour' +%FT%TZ) \
  --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum --output json
```

## Layer 4: Listener rules (weighted routing)

```bash
# All listener rules with forward actions
aws elbv2 describe-rules \
  --listener-arn <listener-arn> --output json | \
  jq '.Rules[] | {
    RuleArn, Priority, IsDefault,
    Conditions: .Conditions,
    Actions: [.Actions[] | {
      Type,
      TargetGroupArn,
      ForwardConfig: .ForwardConfig.TargetGroups
    }]
  }'

# List all listeners for the ALB
aws elbv2 describe-listeners \
  --load-balancer-arn <alb-arn> --output json | \
  jq '.Listeners[] | {
    ListenerArn, Protocol, Port, DefaultActions
  }'
```

## Layer 5: Lambda target group diagnosis

```bash
# Lambda function configuration
aws lambda get-function-configuration \
  --function-name <function-arn> --output json | \
  jq '{State, LastUpdateStatus, Timeout, Runtime, MemorySize}'

# Recent Lambda errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/<function-name> \
  --start-time $(date -d '-30 minutes' +%s)000 \
  --filter-pattern '"Task timed out" OR "Runtime.ExitError" OR "Error"' \
  --output json

# Lambda invocation metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=<function-name> \
  --start-time $(date -d '-1 hour' +%FT%TZ) \
  --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum --output json

# Lambda duration vs timeout
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=<function-name> \
  --start-time $(date -d '-1 hour' +%FT%TZ) \
  --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json
```

## Layer 6: Network ACL verification

```bash
# NACLs for the target subnet
aws ec2 describe-network-acls \
  --filters Name=association.subnet-id,Values=<target-subnet-id> \
  --output json | \
  jq '.NetworkAcls[] | {
    NaclId, Entries: .Entries
  }'

# NACLs for the ALB subnet
aws ec2 describe-network-acls \
  --filters Name=association.subnet-id,Values=<alb-subnet-id> \
  --output json | \
  jq '.NetworkAcls[] | {
    NaclId, Entries: .Entries
  }'
```

NACLs are stateless — both inbound AND outbound rules must allow:
- Inbound: ephemeral ports (1024-65535) for return traffic
- Outbound: health check port + ephemeral ports

## Layer 7: Direct target verification

```bash
# From the target instance itself:
# Check if application is listening
ss -tlnp | grep <port>
# or
netstat -tlnp | grep <port>

# Curl the health endpoint locally
curl -v http://localhost:<port><health-check-path>
curl -s -o /dev/null -w "%{http_code}\n" \
  http://localhost:<port><health-check-path>

# Check application process status
systemctl status <service-name>
ps aux | grep <process-name>

# Check if the application is crash-looping
journalctl -u <service-name> --since "30 minutes ago" | tail -50
```

---

## Pre-flight: account-wide gather-info commands (moved from SKILL.md)

```bash
# 1. Target group configuration (TargetType, HealthCheckPath,
#    HealthCheckPort, HealthCheckProtocol, HealthCheckTimeoutSeconds,
#    HealthCheckIntervalSeconds, HealthyThresholdCount,
#    UnhealthyThresholdCount, Matcher, Protocol, Port, VpcId)
aws elbv2 describe-target-groups \
  --target-group-arns <tg-arn> --output json

# 2. Target health for all registered targets
aws elbv2 describe-target-health \
  --target-group-arn <tg-arn> --output json

# 3. Target group attributes (deregistration delay, stickiness,
#    proxy protocol, preserve client IP, slow start)
aws elbv2 describe-target-group-attributes \
  --target-group-arn <tg-arn> --output json

# 4. Security groups for the targets (ingress rules)
aws ec2 describe-security-groups \
  --group-ids <target-sg-id> --output json

# 5. ALB configuration (subnets, security groups, AZs)
aws elbv2 describe-load-balancers \
  --load-balancer-arns <alb-arn> --output json

# 6. Listener rules (weighted routing, host-header, path-pattern)
aws elbv2 describe-rules \
  --listener-arn <listener-arn> --output json

# 7. CloudWatch target health metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name UnHealthyHostCount \
  --dimensions Name=TargetGroup,Value=<tg-id> Name=LoadBalancer,Value=<alb-id> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum,Maximum --output json
```

## Target-health-state short-circuit (moved from SKILL.md)

| TargetHealth `State` / `Reason` | Effect on diagnosis |
|---|---|
| `healthy` | Target passed health checks. If app still fails, the issue is routing (listener rules), not health. |
| `unhealthy` + `Target.FailedHealthChecks` | Health checker reached the target but the response did not match the expected status code (Matcher). Check path, port, protocol, and the application's actual response. |
| `unhealthy` + `Target.ConnectionFailed` | Health checker could not establish a TCP connection. Check security group, health check port, and target instance state. |
| `unhealthy` + `Target.InvalidState` | The target EC2 instance is stopped or terminated. Check EC2 instance state; not a health check config issue. |
| `unused` | The target is registered but not receiving traffic. Check listener rules (weighted routing), target group attachment to a listener, and cross-zone settings. |
| `draining` | The target was deregistered and is completing in-flight requests. Check `deregistration_delay.timeout_seconds`; not a health check failure. |
| `initial.health_check` (ALB) / `healthy.initial` (NLB) | The target is in the initial health check grace period. Wait for `HealthyThresholdCount` consecutive successes before declaring an issue. |

## Step 2a: Read the health check configuration

```bash
aws elbv2 describe-target-groups \
  --target-group-arns <tg-arn> --output json | \
  jq '.TargetGroups[] | {
    HealthCheckPath, HealthCheckPort, HealthCheckProtocol,
    HealthCheckTimeoutSeconds, HealthCheckIntervalSeconds,
    HealthyThresholdCount, UnhealthyThresholdCount,
    Matcher, Protocol, Port, TargetType, VpcId
  }'
```

## Step 2a: Config-field common-mismatch cross-reference

Cross-reference each field against the application's actual
configuration:

| Config field | Common mismatch |
|---|---|
| `HealthCheckPath` | Application serves `/healthz` but TG configured with `/health` (or vice versa). Case-sensitive. |
| `HealthCheckPort` | Set to `traffic-port` (default) but the app serves health on a different port than the data port. |
| `HealthCheckProtocol` | Set to HTTP but the app only serves HTTPS (or vice versa). |
| `Matcher.HttpCode` | Defaults to `200`; app returns `204`, `301`, or another code. |
| `HealthCheckTimeoutSeconds` | Too short for the app's health endpoint response time (default 5s for HTTP, 2s for HTTPS but must be < interval). |
| `Protocol` (target protocol) | TG protocol HTTP but app expects HTTPS, or TG protocol HTTPS but app serves HTTP. |

## Step 2b: Verify the health check path and response

```bash
# From a host in the same VPC, curl the target's health endpoint directly
curl -v http://<target-private-ip>:<target-port><health-check-path>
curl -v http://<target-private-ip>:<health-check-port><health-check-path>

# Check the HTTP response code
curl -s -o /dev/null -w "%{http_code}" \
  http://<target-private-ip>:<target-port><health-check-path>
```

## Step 2c: Verify the health check port

```bash
# Verify the application listens on the health check port
# (from the target instance itself)
ss -tlnp | grep <health-check-port>
# or
netstat -tlnp | grep <health-check-port>
```

## Step 2d: Verify the protocol

If `HealthCheckProtocol` is `HTTP` but the application only serves
`HTTPS` (redirects all HTTP to HTTPS), the health check gets a 301
redirect which does not match `Matcher.HttpCode: 200`.

If `HealthCheckProtocol` is `HTTPS` but the application serves
`HTTP`, the TLS handshake fails.

**ROOT_CAUSE_IDENTIFIED** with `LAYER: PROTOCOL_MISMATCH`. Fix: align
`HealthCheckProtocol` with the application's actual protocol.

## Step 3a: Identify the ALB security group and subnets

```bash
aws elbv2 describe-load-balancers \
  --load-balancer-arns <alb-arn> --output json | \
  jq '.LoadBalancers[] | {
    SecurityGroups, AvailabilityZones, VpcId,
    State: .State.Code
  }'
```

## Step 3b: Check the target security group ingress rules

```bash
aws ec2 describe-security-groups \
  --group-ids <target-sg-id> --output json | \
  jq '.SecurityGroups[].IpPermissions'
```

## Step 3b: Fix — authorize ALB SG ingress

```bash
aws ec2 authorize-security-group-ingress \
  --group-id <target-sg-id> \
  --ip-permissions IpProtocol=tcp,FromPort=<health-check-port>,ToPort=<health-check-port>,UserIdGroupPairs=[{GroupId=<alb-sg-id>}]
```

## Step 3c: Verify with ALB ENI IPs

```bash
# Get the ALB's ENI private IPs
aws ec2 describe-network-interfaces \
  --filters Name=description,Values="ELB app/<alb-name>/*" \
  --output json | \
  jq '.NetworkInterfaces[].PrivateIpAddress'
```

## Step 3c: Attempt connection from the target instance

```bash
# From the target instance
curl -v http://<alb-eni-ip>:<health-check-port><health-check-path>
```

## Step 3d: Network ACL check

If the SG is correct but health checks still fail, check the NACL on
both the ALB subnet and the target subnet. NACLs are stateless; both
inbound and outbound rules must allow ephemeral ports (1024-65535) for
return traffic.

## Step 4a: Identify the failing targets' AZs

```bash
aws elbv2 describe-target-health \
  --target-group-arn <tg-arn> --output json | \
  jq '.TargetHealthDescriptions[] | {
    Target: .Target.Id, Port: .Target.Port,
    AZ: .Target.AvailabilityZone,
    Health: .TargetHealth.State,
    Reason: .TargetHealth.Reason
  }'
```

## Step 5: Deregistration delay probe

```bash
aws elbv2 describe-target-group-attributes \
  --target-group-arn <tg-arn> --output json | \
  jq '.Attributes[] | select(.Key | startswith("deregistration"))'
```

## Step 5: Lower the deregistration delay

```bash
aws elbv2 modify-target-group-attributes \
  --target-group-arn <tg-arn> \
  --attributes Key=deregistration_delay.timeout_seconds,Value=60
```

## Step 6a: Read the threshold and interval config

```bash
aws elbv2 describe-target-groups \
  --target-group-arns <tg-arn> --output json | \
  jq '.TargetGroups[] | {
    HealthCheckIntervalSeconds,
    HealthCheckTimeoutSeconds,
    HealthyThresholdCount,
    UnhealthyThresholdCount
  }'
```

## Step 7: Slow start probe

```bash
aws elbv2 describe-target-group-attributes \
  --target-group-arn <tg-arn> --output json | \
  jq '.Attributes[] | select(.Key | startswith("slow_start"))'
```

## Step 8a: Check listener rules for weighted forwarding

```bash
aws elbv2 describe-rules \
  --listener-arn <listener-arn> --output json | \
  jq '.Rules[].Actions[] | select(.Type == "forward") | .ForwardConfig'
```

## Step 8b: Check cross-zone load balancing

```bash
aws elbv2 describe-load-balancer-attributes \
  --load-balancer-arn <alb-arn> --output json | \
  jq '.Attributes[] | select(.Key | startswith("load_balancing"))'
```

## Step 9a: Check the Lambda function health

```bash
aws lambda get-function-configuration \
  --function-name <function-arn> --output json | \
  jq '{State, LastUpdateStatus, Timeout, Runtime}'

aws logs filter-log-events \
  --log-group-name /aws/lambda/<function-name> \
  --start-time $(date -d '-30 minutes' +%s)000 \
  --filter-pattern '"Task timed out" OR "Runtime.ExitError" OR "Error"' \
  --output json
```

## Step 9: Common Lambda target group failure patterns

Common Lambda target group failure patterns:

| Pattern | Cause |
|---|---|
| Function times out on health check invocation | Lambda Timeout too low. The ALB health check is a synchronous invoke; if it times out, the target is unhealthy. |
| Function returns non-200 status code | The function handler returns a response with `statusCode` != 200. The ALB expects 200 for health. |
| Function throws an exception | Unhandled exception in the handler. The ALB receives a 502 from Lambda and marks the target unhealthy. |
| Multi-value headers misconfigured | The function response must properly format headers for the ALB integration. |
| Function does not handle the ALB health check event | The ALB sends a GET request event; the function must be able to handle it and return 200. |
