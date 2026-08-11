# Baseline (no-skill) response: origin-tls-protocol-mismatch-https-only

---

Your CloudFront distribution is returning 502 errors. This usually means
the origin is down or unreachable. Try these steps:

1. Check if the ALB is healthy and has healthy targets registered.
2. Verify the security group on the ALB allows inbound traffic on port
   443.
3. Check the CloudFront distribution's origin settings to make sure the
   domain name is correct.
4. Wait a few minutes — sometimes 502s are transient.

If the issue persists, you may need to contact AWS support.
