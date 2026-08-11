# Baseline (no-skill) — active-directory-full-tunnel

> This is the response a model produces **without** the skill
> definition. It creates the endpoint but does not specify full-tunnel
> mode (defaults to full-tunnel but does not state it), misses the
> authorization rule for group-restricted access, and does not set up
> connection logging. Generated for with-skill-vs-baseline comparison.

---

Create the endpoint:

```bash
aws ec2 create-client-vpn-endpoint \
  --client-cidr-block 10.251.0.0/16 \
  --server-certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/abc123 \
  --authentication-type directory-service-auth \
  --directory-id d-9067a4a4bd
```

Then associate the subnet.
