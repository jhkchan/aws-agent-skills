# Diagnostic Commands — Route 53 ARC Deployer

Verification and monitoring commands moved out of the SKILL.md body. Loaded on demand.


## Verify routing control state (Step 3)

```bash
aws route53-recovery-cluster get-routing-control-state \
  --routing-control-arn "$RC_A_ARN"
# Expected: RoutingControlState: "On"
```


## Get readiness status (Step 5)

```bash
aws route53-recovery-readiness get-readiness-check \
  --readiness-check-name "app-readiness-check"

# Get readiness for a specific cell
aws route53-recovery-readiness get-cell-readiness \
  --cell-name "Cell-B"
```


## Create multiple readiness checks, one per resource set (Step 5)

```bash
for RS_NAME in app-nlb-resource-set app-asg-resource-set app-ddb-resource-set; do
  aws route53-recovery-readiness create-readiness-check \
    --readiness-check-name "${RS_NAME}-check" \
    --resource-set-name "$RS_NAME"
done
```


## Create a CloudWatch alarm for routing control state change (Step 7)

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "arc-routing-control-changed" \
  --namespace AWS/Route53RecoveryControl \
  --metric-name RoutingControlState \
  --dimensions Name=RoutingControlName,Value=cell-a-traffic \
  --statistic Maximum \
  --period 60 \
  --evaluation-periods 1 \
  --threshold 0 \
  --comparison-operator LessThanThreshold \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:arc-alerts"
```

This alarm fires when Cell-A's routing control transitions from ON
(1) to OFF (0), alerting the team of a failover event.
