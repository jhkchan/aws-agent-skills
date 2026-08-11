# Eval prompt: full-stack-org-policy

Design a complete tag compliance automation baseline for the following
organization. Emit the standard COMPLIANCE block (POLICY, DETECTION,
AUTOMATION, PROPAGATION, COST, CROSS_ACCOUNT, VERDICT, GAP, TEMPLATE).

Design reference: full-stack-org-policy
Organization ID: o-xxxxxxx
Root ID: r-xxxx
Account: 111111111111 (payer), 222222222222 (member)
Region: us-east-1

Required tags: Environment, Owner, CostCenter, Project, Application.
Environment allowed_values: dev, staging, prod.
CostCenter allowed_values: cc-100, cc-200, cc-300.
Target resource types: EC2 instances, S3 buckets, RDS instances, Lambda functions.
SSM service role ARN: arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole
Auto-tagger Lambda role ARN: arn:aws:iam::111111111111:role/AutoTaggerRole
Pre-prod validation: completed for auto-tagger (EC2->EBS/ENI propagation tested).
Cost allocation tags: API activation confirmed available (Billing IAM access enabled).
