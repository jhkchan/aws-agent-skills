# ELB Optimization Commands — Reference

Supplementary reference for the ELB Cost Optimizer skill. The
canonical command script per optimization dimension.

## Universal first commands (run for any ELB cost review)

```bash
# 1. List all ALBs and NLBs:
aws elbv2 describe-load-balancers \
  --query 'LoadBalancers[*].{name:LoadBalancerName,arn:LoadBalancerArn,type:Type,scheme:Scheme,vpc:VpcId,dns:DNSName,state:State.Code,created:CreatedTime}'

# 2. List all CLBs (legacy):
aws elb describe-load-balancers \
  --query 'LoadBalancerDescriptions[*].{name:LoadBalancerName,dns:DNSName,scheme:Scheme,created:CreatedTime,listeners:ListenerDescriptions[*].{lbport:LoadBalancerPort,prot:Protocol,instport:InstancePort,instprot:InstanceProtocol}}'

# 3. List listeners and rules for each ALB:
aws elbv2 describe-listeners \
  --load-balancer-arn <lb-arn> \
  --query 'Listeners[*].{arn:ListenerArn,port:Port,prot:Protocol,ssl:Certificates,default:DefaultActions,rules:Rules}'

aws elbv2 describe-rules \
  --listener-arn <listener-arn> \
  --query 'Rules[*].{arn:RuleArn,priority:Priority,conditions:Conditions,actions:Actions}'

# 4. List target groups:
aws elbv2 describe-target-groups \
  --load-balancer-arn <lb-arn> \
  --query 'TargetGroups[*].{name:TargetGroupName,arn:TargetGroupArn,prot:Protocol,port:Port,health:HealthCheckPath,tgtype:TargetType}'

# 5. Pull 14-day LCU consumption (ALB):
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name ConsumedLCUs \
  --dimensions Name=LoadBalancer,Value=<lb-full-name> \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 \
  --statistics Average Maximum
```

## Dimension A: Idle LB detection

```bash
# ALB request count (14-day daily sum):
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name RequestCount \
  --dimensions Name=LoadBalancer,Value=<lb-full-name> \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 86400 \
  --statistics Sum \
  --query 'Datapoints[*].{time:Timestamp,sum:Sum}'

# Healthy host count (14-day):
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name HealthyHostCount \
  --dimensions Name=LoadBalancer,Value=<lb-full-name> Name=TargetGroup,Value=<tg-full-name> \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 \
  --statistics Average Minimum

# Check Route 53 records pointing to the LB:
aws route53 list-resource-record-sets \
  --hosted-zone-id <zone-id> \
  --query 'ResourceRecordSets[?contains(ResourceRecords[].Value, `<lb-dns-name>`)]'

# Tag the LB for 7-day observation before deletion:
aws elbv2 add-tags \
  --resource-arns <lb-arn> \
  --tags Key=pending-deletion,Value=true Key=deletion-date,Value=2026-08-18

# Delete the confirmed idle ALB:
aws elbv2 delete-load-balancer --load-balancer-arn <lb-arn>
```

## Dimension B: LCU per-dimension analysis

```bash
# New connections per second (14-day hourly):
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name NewConnectionCount \
  --dimensions Name=LoadBalancer,Value=<lb-full-name> \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average Maximum

# Active connections:
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name ActiveConnectionCount \
  --dimensions Name=LoadBalancer,Value=<lb-full-name> \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average Maximum

# Processed bytes:
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name ProcessedBytes \
  --dimensions Name=LoadBalancer,Value=<lb-full-name> \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average Maximum

# Rule evaluations:
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name RuleEvaluations \
  --dimensions Name=LoadBalancer,Value=<lb-full-name> \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average Maximum
```

## Dimension C: ALB consolidation via multi-path routing

```bash
# Create a host-based listener rule on the consolidated ALB:
aws elbv2 create-rule \
  --listener-arn <listener-arn> \
  --priority 10 \
  --conditions Field=host-header,Values='api.example.com' \
  --actions Type=forward,TargetGroupArn=<api-tg-arn>

# Create a path-based rule:
aws elbv2 create-rule \
  --listener-arn <listener-arn> \
  --priority 20 \
  --conditions Field=path-pattern,Values='/admin/*' \
  --actions Type=forward,TargetGroupArn=<admin-tg-arn>

# Modify the ALB idle timeout (reduce active connections):
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn <lb-arn> \
  --attributes Key=idle_timeout.timeout_seconds,Value=30
```

## Dimension D: CLB to ALB migration

```bash
# Describe the CLB for migration planning:
aws elb describe-load-balancers \
  --load-balancer-names <clb-name> \
  --query 'LoadBalancerDescriptions[*].{name:LoadBalancerName,listeners:ListenerDescriptions,instances:Instances,scheme:Scheme,subnets:Subnets,sg:SecurityGroups}'

# Create the target group for the new ALB:
aws elbv2 create-target-group \
  --name migrated-tg \
  --protocol HTTP \
  --port 80 \
  --vpc-id <vpc-id> \
  --health-check-path /health \
  --health-check-interval-seconds 30

# Create the replacement ALB:
aws elbv2 create-load-balancer \
  --name migrated-alb \
  --subnets <subnet-1> <subnet-2> \
  --security-groups <sg-id> \
  --scheme internet-facing \
  --type application

# Create the HTTPS listener with the ACM certificate:
aws elbv2 create-listener \
  --load-balancer-arn <new-alb-arn> \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=<cert-arn> \
  --default-actions Type=forward,TargetGroupArn=<tg-arn>
```

## Dimension E: NLB cross-zone and data transfer

```bash
# Check NLB cross-zone load balancing state:
aws elbv2 describe-load-balancer-attributes \
  --load-balancer-arn <nlb-arn> \
  --query 'Attributes[?Key==`load_balancing.cross_zone.enabled`]'

# Disable cross-zone on an NLB (saves $0.01/GB cross-AZ traffic):
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn <nlb-arn> \
  --attributes Key=load_balancing.cross_zone.enabled,Value=false

# NLB processed bytes (14-day):
aws cloudwatch get-metric-statistics \
  --namespace AWS/NetworkELB \
  --metric-name ProcessedBytes \
  --dimensions Name=LoadBalancer,Value=<nlb-full-name> \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Sum
```

## Dimension F: Access log S3 lifecycle

```bash
# Check current ALB access log configuration:
aws elbv2 describe-load-balancer-attributes \
  --load-balancer-arn <lb-arn> \
  --query 'Attributes[?Key==`access_logs.s3.enabled` || Key==`access_logs.s3.bucket`]'

# Add S3 lifecycle rule for access log cost reduction:
aws s3api put-bucket-lifecycle-configuration \
  --bucket <log-bucket> \
  --lifecycle-configuration '{
    "Rules": [
      {
        "Id": "alb-access-logs-lifecycle",
        "Status": "Enabled",
        "Filter": {"Prefix": "AWSLogs/"},
        "Transitions": [
          {"Days": 30, "StorageClass": "STANDARD_IA"},
          {"Days": 90, "StorageClass": "GLACIER"}
        ],
        "Expiration": {"Days": 365}
      }
    ]
  }'
```

## Verification commands (post-optimization)

```bash
# Verify LCU reduction after enabling keep-alive (7-day check):
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name ConsumedLCUs \
  --dimensions Name=LoadBalancer,Value=<lb-full-name> \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average Maximum

# Check ALB 5xx error rate after consolidation:
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name HTTPCode_ELB_5XX_Count \
  --dimensions Name=LoadBalancer,Value=<lb-full-name> \
  --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Sum

# Verify target health after consolidation:
aws elbv2 describe-target-health \
  --target-group-arn <tg-arn> \
  --query 'TargetHealthDescriptions[*].{target:Target.Id,port:Target.Port,state:TargetHealth.State}'
```
