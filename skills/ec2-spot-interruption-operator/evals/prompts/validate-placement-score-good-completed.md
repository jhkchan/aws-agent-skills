# Eval prompt: validate-placement-score-good-completed

Validate the Spot placement score for the proposed fleet configuration and
emit the standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS,
STEPS, POST_VERIFY, NOTES).

Operation: validate-placement-score
Target capacity: 100 Spot Instances
Region: us-east-1

```json
{
  "ProposedConfig": {
    "InstanceTypes": ["m6a.large", "m6i.large", "c6g.large"],
    "AZs": ["us-east-1a", "us-east-1b", "us-east-1c"],
    "TotalPools": "9 (3 families x 3 AZs)"
  },
  "SpotPlacementScoreResult": {
    "Score": 9,
    "Context": "Highly recommended — sufficient capacity for the requested 100 instances across the diversified pools"
  },
  "FleetLaunchReadiness": {
    "LaunchTemplate": "lt-web-prod version 3 exists",
    "AMIValidation": "passed (ami-0webprod, Amazon Linux 2023)",
    "IAMInstanceProfile": "prod-web-profile (SSM + S3 checkpoint perms)",
    "SecurityGroup": "sg-web-prog (ingress 443 from ALB)",
    "KeyPair": "none (SSM Session Manager only)"
  }
}
```
