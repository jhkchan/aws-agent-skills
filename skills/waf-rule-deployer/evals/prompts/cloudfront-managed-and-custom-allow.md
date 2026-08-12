# Eval: cloudfront-managed-and-custom-allow

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — CloudFront scope us-east-1, managed rule groups (CommonRuleSet/SQLi/IPReputation), custom allow at priority 0 before geo block at priority 40, WCU budget cited, logging via Firehose aws-waf-logs-*

## Prompt

Create a CloudFront Web ACL named production-cloudfront-acl
protecting distribution E1234567890 in account 123456789012.
Add AWSManagedRulesCommonRuleSet, AWSManagedRulesSQLiRuleSet,
and AWSManagedRulesAmazonIpReputationList managed rule groups.
Add a custom allow rule for partner CIDRs (IP set partner-cidrs
with 203.0.113.0/24 and 198.51.100.10/32) at priority 0.
Add a custom block for high-risk geos RU and KP at priority 40.
Enable logging to Firehose aws-waf-logs-production (S3 bucket
waf-logs-bucket, redact Authorization header). Default action
ALLOW. Tags: Environment=production, Protected=cloudfront.
