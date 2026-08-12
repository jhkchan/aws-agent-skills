# Eval: lambda-target-with-domain-and-logs

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — LAMBDA target group, custom domain with ACM cert in us-east-1, access logs to CloudWatch

## Prompt

Create a Lambda target group tg-processor for function
arn:aws:lambda:us-east-1:123456789012:function:processor. Attach
to service events-svc (svc-eee555). Custom domain
events.internal.example.com with ACM cert
arn:aws:acm:us-east-1:123456789012:certificate/aaa-bbb-ccc.
Enable access logs to CloudWatch log group /aws/vpc-lattice.
us-east-1.
