# Eval: ebextensions-rds-config

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — .ebextensions with options, RDS (Retain), hooks, rolling+additional batch

## Prompt

Create an Elastic Beanstalk environment named myapp-api for application
myapp in us-east-1. Platform: 64bit Amazon Linux 2023 v6.0.4 running
Node.js 20. The source bundle includes .ebextensions/01-options.config
(NODE_ENV=production), .ebextensions/02-rds.config (PostgreSQL
db.t3.micro, DeletionPolicy Retain), and .ebextensions/03-hooks.config
(npm run migrate, leader_only). Deployment policy: rolling with
additional batch. ALB, enhanced health. ASG: min=2, max=6. VPC
vpc-aaa11122, subnets subnet-aaa, subnet-bbb.
