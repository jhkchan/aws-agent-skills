# Diagnostic and Pre-flight Commands - wafv2-web-acl-auditor

## Pre-flight safety checks (moved from SKILL.md)

- Confirm the Web ACL exists and capture its current state:
  `aws wafv2 describe-web-acl --id <id> --scope <CLOUDFRONT|REGIONAL> --output json > /tmp/<name>-backup-$(date +%s).json`.
  This backup is the rollback target.
- Check resource associations before modifying rules:
  `aws wafv2 list-resources-for-web-acl --web-acl-arn <arn> --output json`.
  An ACL attached to a production CloudFront distribution or ALB affects
  live traffic immediately upon update.
- Prefer additive changes (add a rule group) over destructive changes
  (delete a rule, switch Allow to Block). Adding a managed rule group in
  COUNT mode first, monitoring for a week, then switching to BLOCK is the
  safe progression. Deleting a rule or changing the default action is a
  live-traffic-impacting change.
- For shadow-rule remediation (Step 2), do NOT delete the shadow rule
  without understanding why it was added. It may be load-bearing for a
  legitimate traffic class (e.g., a partner integration that sends a
  specific header). Replace the broad match with a scoped match before
  removing the rule.
- Web ACL updates are eventually consistent — allow 60 seconds for
  changes to propagate to all edge locations before testing. Do not
  re-deploy or iterate within that window.
