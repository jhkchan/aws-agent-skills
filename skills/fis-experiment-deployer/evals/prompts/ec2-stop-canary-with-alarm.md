# Eval: ec2-stop-canary-with-alarm

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — fis-target=true tag, alarm in OK state, role has DescribeAlarms, tag-scoped role

## Prompt

Create an FIS experiment template named "ec2-stop-canary" in
us-east-1, account 111111111111. Stop one EC2 instance tagged
fis-target=true (currently 1 instance i-0abc123) for 60 seconds.
Stop condition: alarm "fis-stop-error-rate" (currently OK, FIS
role already has cloudwatch:DescribeAlarms on it). Log to S3
bucket "fis-logs-111111111111" prefix "experiments/" and CloudWatch
Logs group "/aws/fis/ec2-stop-canary". budgetDuration 2 minutes.
