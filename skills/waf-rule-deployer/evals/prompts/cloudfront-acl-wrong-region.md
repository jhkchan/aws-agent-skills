# Eval: cloudfront-acl-wrong-region

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — CloudFront scope requires us-east-1; operator specified us-west-2

## Prompt

Create a CloudFront Web ACL named cdn-protection in us-west-2
protecting distribution E9876543210. Add
AWSManagedRulesCommonRuleSet and AWSManagedRulesSQLiRuleSet.
Default action BLOCK. Account 123456789012.
