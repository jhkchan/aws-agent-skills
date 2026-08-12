# Eval: ssm-session-manager-cloudwatch

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — SSM Session Manager as recommended access method (not SSH), CloudWatch agent manually installed on each on-prem node

## Prompt

Enable SSM Session Manager for remote access to 3 EKS hybrid
nodes on prod-cluster. Also install CloudWatch agent for health
monitoring. Hybrid node IAM role EKSHybridNodeRole with SSM and
CloudWatch permissions. us-east-1.
