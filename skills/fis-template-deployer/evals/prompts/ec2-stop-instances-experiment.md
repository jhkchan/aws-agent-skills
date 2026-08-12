# Eval: ec2-stop-instances-experiment

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — aws:ec2:stop-instances action on tag FIS_Target=enabled in staging, COUNT(1) selectionMode, CloudWatch CPU-high alarm stop condition, IAM role scoped to ec2:StopInstances on the FIS_Target tag

## Prompt

Create a FIS experiment template in us-east-1 account
123456789012. Action: aws:ec2:stop-instances with startAfter 5m.
Target: EC2 instances tagged FIS_Target=enabled and
Environment=staging, selectionMode COUNT(1). Stop condition:
CloudWatch alarm FIS-CPU-High (alarm ARN
arn:aws:cloudwatch:us-east-1:123456789012:alarm:FIS-CPU-High).
IAM role FISExperimentRole (trust fis.amazonaws.com,
ec2:StopInstances on tag FIS_Target=enabled). Log group
/aws/fis/stop-instance-experiment. Tags: Environment=staging,
ExperimentType=HA-Test.
