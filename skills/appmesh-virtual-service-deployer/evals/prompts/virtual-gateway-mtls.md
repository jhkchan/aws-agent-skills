# Eval: virtual-gateway-mtls

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — virtual gateway with mTLS STRICT mode, ACM Private CA referenced, gateway route to virtual service

## Prompt

Create an App Mesh virtual gateway ingress-gateway in mesh
production-mesh (us-east-1). Listener port 8443 https. mTLS
STRICT mode via ACM Private CA (ca-arn
arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/
abc123). Gateway route checkout-ingress to virtual service
checkout.mesh.local (prefix /checkout). Account 123456789012.
