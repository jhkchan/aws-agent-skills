# Eval: org-aggregator-delegated-admin

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — OrganizationAggregationSource, delegated admin, all-region source, org conformance pack, Lambda processor org config rule

## Prompt

Provision an AWS Config aggregator in us-east-1. Name:
org-compliance-aggregator. Type: organization aggregator.
Organization ID: o-abc123def. Delegated administrator
account: 123456789012. Source: all accounts in the
organization, all AWS regions. Conformance pack:
OperationalBestPractices-for-Security deployed at
organization level from S3 template
s3://config-templates-123456789012/security-best-practices.yaml.
Organization config rule: tag-policy-compliance (Lambda
processor, function config-tag-policy-rule). Tags:
Environment=production, Governance=compliance.
