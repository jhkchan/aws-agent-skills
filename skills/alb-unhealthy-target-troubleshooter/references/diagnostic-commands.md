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
