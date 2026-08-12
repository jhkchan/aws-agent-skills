# Baseline (no-skill) — virtual-gateway-mtls

> This is the response a model produces **without** the skill
> definition. It creates the virtual gateway but does not flag that
> mTLS STRICT mode requires SDS (Secret Discovery Service) to
> distribute certificates to Envoy (connections will be rejected
> without it), does not verify the ACM Private CA is ACTIVE, and
> omits the READY_TO_DEPLOY checklist format. Generated for with-
> skill-vs-baseline comparison.

---

Create the virtual gateway with mTLS:

```bash
aws appmesh create-virtual-gateway --mesh-name production-mesh \
  --virtual-gateway-name ingress-gateway \
  --spec '{"listeners":[{"portMapping":{"port":8443,"protocol":"https"},"tls":{"mode":"STRICT","certificate":{"acm":{"certificateArn":"arn:aws:acm:us-east-1:123456789012:certificate/abc"}}}}]}'
```

Then add the gateway route.
