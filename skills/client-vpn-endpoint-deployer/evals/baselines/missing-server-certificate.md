# Baseline (no-skill) — missing-server-certificate

> This is the response a model produces **without** the skill
> definition. It attempts to create the endpoint without a server
> certificate, which will fail at runtime (API error). The model does
> not detect the missing prerequisite proactively. Generated for
> with-skill-vs-baseline comparison.

---

Create the endpoint:

```bash
aws ec2 create-client-vpn-endpoint \
  --client-cidr-block 10.250.0.0/16 \
  --authentication-type certificate-mutual-auth
```

This will fail because `--server-certificate-arn` is required for
mutual TLS authentication.
