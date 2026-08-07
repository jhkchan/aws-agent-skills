# Baseline (no-skill) response: origin-group-failover

This file captures what a generic assistant produces WITHOUT the
cloudfront-distribution-deployer skill loaded — the contrast that proves
the skill adds structure (origin group with explicit failover status
codes, https-only origin protocol policy, security headers policy,
real-time logging to OpenSearch for switch-over detection).

---

To set up multi-region failover with CloudFront, you can use an origin
group with your primary and secondary ALBs.

Architecture:

- Primary: prod-alb-us-east-1.us-east-1.elb.amazonaws.com
- Secondary: prod-alb-us-west-2.us-west-2.elb.amazonaws.com
- Failover: when primary fails
- HTTPS for viewers

Steps:

1. Create the distribution with both origins.
2. Configure an origin group for failover.
3. Set the primary and secondary.
4. Deploy.

CloudFront will automatically route to the secondary if the primary
returns errors. You can also add a WAF and security headers.

The failover should cover your DR scenario. The secondary ALB will
handle traffic when us-east-1 is down.
