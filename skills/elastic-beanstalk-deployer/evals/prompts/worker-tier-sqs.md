# Eval: worker-tier-sqs

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Worker tier, SQS daemon, queue-depth auto scaling, no ELB

## Prompt

Create a worker tier Elastic Beanstalk environment named myapp-worker
for application myapp in us-east-1. Platform: 64bit Amazon Linux 2023
v6.0.4 running Python 3.11. Application version v1 from
s3://myapp-deploy/app-worker-v1.zip. SQS queue:
arn:aws:sqs:us-east-1:123456789012:myapp-jobs. Auto scaling on queue
depth: lower=1, upper=10. ASG: min=1, max=4. Service role:
aws-elasticbeanstalk-service-role. Instance profile:
aws-elasticbeanstalk-ec2-role. Tags: Environment=production,
Tier=worker.
