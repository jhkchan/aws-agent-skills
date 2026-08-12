# Eval: network-connectivity-disruption

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — aws:network:disrupt-connectivity action between us-east-1a and us-east-1b, FIS network agent IAM role with ec2:CreateNetworkInterface, CloudWatch health-check alarm stop condition

## Prompt

Create a FIS experiment template in us-east-1 account
123456789012. Action: aws:network:disrupt-connectivity with
duration 2m, scope between us-east-1a and us-east-1b in VPC
vpc-aaa11122. Stop condition: CloudWatch alarm
FIS-HealthCheck-Fail (ARN
arn:aws:cloudwatch:us-east-1:123456789012:alarm:FIS-HealthCheck-Fail).
IAM role FISNetworkRole with ec2:CreateNetworkInterface and
ec2:DeleteNetworkInterface permissions plus FIS network agent
pass-role. Log group /aws/fis/network-disruption. Tags:
Environment=staging, ExperimentType=MultiAZ-Network.
