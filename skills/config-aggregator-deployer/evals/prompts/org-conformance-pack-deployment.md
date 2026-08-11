# Eval: org-conformance-pack-deployment

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — org-level conformance pack deployment with custom parameters, existing aggregator

## Prompt

Deploy a conformance pack at the organization level in
us-east-1 on delegated admin account 123456789012.
Organization aggregator org-compliance-aggregator already
exists. Conformance pack name: OperationalBestPractices-
for-EC2. Template S3 URI: s3://config-templates-123456789012
/ec2-best-practices.yaml. Input parameters:
DesiredInstanceType=t3.medium, AllowedRegions=us-east-1.
Deploy to all accounts in the organization. Tags:
Environment=production.
