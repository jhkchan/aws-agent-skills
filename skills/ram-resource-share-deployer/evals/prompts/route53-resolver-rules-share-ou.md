# Eval: route53-resolver-rules-share-ou

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — route53resolver:ResolverRule, OU ARN principal, auto-applies to accounts in OU

## Prompt

Provision a RAM resource share in us-east-1. Name:
shared-resolver-rules-ou. Resource type:
route53resolver:ResolverRule. Resource ARN:
arn:aws:route53resolver:us-east-1:123456789012:resolver-rule/
rslvr-rr-abc123. Principals: OU
arn:aws:organizations::123456789012:ou/o-abc123def/ou-xyz456.
All features enabled. Allow external principals: false. Use
default managed permission for Resolver Rules. Tags:
Environment=production, Application=dns.
