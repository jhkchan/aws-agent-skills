# Error Handling - waf-rule-deployer

## WAF failure deep dives (moved from SKILL.md 'Error handling')

### WAFInvalidParameterException: WCU limit exceeded
- Total WCU exceeds 1500. Offload to a referenced rule group, remove
  low-value managed groups, or request a limit increase via Support.

### Association fails for CloudFront distribution
- ACL scope is not CLOUDFRONT, or ACL is not in us-east-1. Scope and
  region are immutable; recreate with `--scope CLOUDFRONT --region
  us-east-1`.

### put-logging-configuration fails
- Firehose stream name does not start with `aws-waf-logs-`. Rename
  or recreate with the required prefix. Verify the stream is in the
  same region as the ACL.

### Custom rule referencing IP set fails
- IP set is in a different scope or region. Recreate in the same
  scope and region.

### Rate-based rule not triggering
- Rate window is fixed at 5 minutes. Verify the limit is not too
  high for the traffic volume. Behind a proxy, switch to
  `FORWARDED_IP` with `X-Forwarded-For`.

### Managed rule group pinned, no new signatures
- Pinned versions do not receive updates. Use
  `describe-managed-rule-group` to see available versions and
  upgrade quarterly.
