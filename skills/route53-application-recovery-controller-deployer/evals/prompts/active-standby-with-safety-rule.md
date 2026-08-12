# Eval: active-standby-with-safety-rule

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — two-cell active-standby with OR safety rule, readiness checks, NLB and ASG resource sets

## Prompt

Create a Route 53 ARC setup for my application. Two cells:
Cell-A in us-east-1 and Cell-B in us-west-2. Active-standby
topology with Cell-A as primary. Recovery cluster name
app-recovery-cluster. Resource sets: NLB
(AWS::ElasticLoadBalancingV2::LoadBalancer) with ARNs
arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/net/app-nlb-a/50dc6c495c0c9188
and
arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/net/app-nlb-b/60dc6c495c0c9189.
ASG (AWS::AutoScaling::AutoScalingGroup) with ARNs
arn:aws:autoscaling:us-east-1:123456789012:autoScalingGroup:...:asg-a
and
arn:aws:autoscaling:us-west-2:123456789012:autoScalingGroup:...:asg-b.
Need a safety rule to prevent total outage. Tags:
Environment=production, Application=app.
