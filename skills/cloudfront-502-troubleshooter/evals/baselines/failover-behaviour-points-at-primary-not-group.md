# Baseline (no-skill) response: failover-behaviour-points-at-primary-not-group

---

Your CloudFront distribution is returning 502 when the primary origin
fails. If you have configured a failover group, check:

1. The OriginGroup configuration in the CloudFront distribution.
2. That both origins are listed as members.
3. The failover criteria status codes.
4. The health of the secondary origin.

If the secondary is not receiving traffic, you may need to verify the
CacheBehavior is configured correctly to use the group.
