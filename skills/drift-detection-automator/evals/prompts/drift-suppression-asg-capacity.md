# Eval prompt: drift-suppression-asg-capacity

Design a drift detection workflow with suppression rules for known-
acceptable changes. Emit the standard DRIFT_AUTOMATION block.

Design reference: drift-suppression-asg-capacity
Account: 111111111111
Region: us-east-1

Stack: prod-api-service (CloudFormation, 28 resources)
Environment: production
Known-acceptable drift: ASG DesiredCapacity changes (scheduled scaling),
  Lambda alias RoutingConfig (canary deployments)
These should be suppressed from CRITICAL severity classification.
All other drift should be classified normally.
