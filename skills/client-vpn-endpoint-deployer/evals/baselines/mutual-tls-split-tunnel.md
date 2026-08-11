# Baseline (no-skill) — mutual-tls-split-tunnel

> This is the response a model produces **without** the skill
> definition. It creates the endpoint but misses the custom DNS
> server requirement for split-tunnel (DNS leak), the authorization
> rule (connected clients cannot reach any network without it), the
> subnet association prerequisite, and the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Create the endpoint:

```bash
aws ec2 create-client-vpn-endpoint \
  --client-cidr-block 10.250.0.0/16 \
  --server-certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/abc123 \
  --authentication-type certificate-mutual-auth \
  --split-tunnel
```

Then associate the subnet and add routes.
