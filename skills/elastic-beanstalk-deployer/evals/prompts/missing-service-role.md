# Eval: missing-service-role

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — service role does not exist; environment creation will fail

## Prompt

Create an Elastic Beanstalk environment named myapp-prod for application
myapp in us-east-1. Platform: 64bit Amazon Linux 2023 v6.0.4 running
Node.js 20. Application version v2 from s3://myapp-deploy/app-v2.zip.
The service role aws-elasticbeanstalk-service-role does not exist yet.
VPC vpc-aaa11122, subnets subnet-aaa, subnet-bbb.
