# Eval: missing-iam-role-permissions

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — IAM role FISExperimentRole lacks ec2:StopInstances permission required by the aws:ec2:stop-instances action; experiment would fail to start with permission denied

## Prompt

Create a FIS experiment template in us-east-1 account
123456789012. Action: aws:ec2:stop-instances. Target: EC2
instances tagged FIS_Target=enabled, selectionMode COUNT(1).
Stop condition: CloudWatch alarm FIS-CPU-High (ARN
arn:aws:cloudwatch:us-east-1:123456789012:alarm:FIS-CPU-High).
IAM role FISExperimentRole — the role has trust policy for
fis.amazonaws.com but only grants ec2:DescribeInstances (no
ec2:StopInstances permission). Log group
/aws/fis/stop-instance-experiment.
