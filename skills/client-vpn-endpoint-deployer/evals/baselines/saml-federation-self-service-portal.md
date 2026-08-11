# Baseline (no-skill) — saml-federation-self-service-portal

> This is the response a model produces **without** the skill
> definition. It attempts SAML federation but misses the server
> certificate requirement (even SAML needs a server cert for TLS),
> the self-service portal enablement flag, and the subnet association
> step. Generated for with-skill-vs-baseline comparison.

---

Create the endpoint with SAML:

```bash
aws ec2 create-client-vpn-endpoint \
  --client-cidr-block 10.250.0.0/16 \
  --authentication-type federated-authentication \
  --saml-provider-arn arn:aws:iam::123456789012:saml-provider/CorporateIdP
```

Then configure access.
