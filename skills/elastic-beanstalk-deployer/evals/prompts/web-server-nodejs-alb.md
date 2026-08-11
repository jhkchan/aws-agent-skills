# Eval: web-server-nodejs-alb

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — AL2023 Node.js, ALB, immutable policy, enhanced health, managed updates, VPC subnets, ASG

## Prompt

Create an Elastic Beanstalk environment named myapp-prod for
application myapp in us-east-1. Platform: 64bit Amazon Linux 2023
v6.0.4 running Node.js 20. Application version v2 from
s3://myapp-deploy/app-v2.zip. Load balancer: ALB. Deployment
policy: immutable. Enhanced health reporting: enabled. Managed
updates: enabled, minor level, Mon:02:00 window. VPC vpc-aaa11122
with subnets subnet-aaa, subnet-bbb. Security group sg-app-prod.
ASG: min=2, max=8, CPUUtilization 20-80%. Tags: Environment=production,
App=myapp.
