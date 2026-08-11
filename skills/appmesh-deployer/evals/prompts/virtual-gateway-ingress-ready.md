# Eval prompt: virtual-gateway-ingress-ready

Plan the virtual gateway deployment and emit the standard VERDICT
block.

Operation: deploy-gateway
Mesh: prod-checkout-mesh (already exists)
Region: us-east-1
Virtual gateway: ingress-gateway
Listener: HTTPS port 8443, ACM cert arn:aws:acm:us-east-1:111111111111:certificate/abc123
Mode: PERMISSIVE (migration phase)
Gateway route: checkout-ingress (HTTP prefix /checkout -> checkout virtual service)
ALB target group: tg-ingress-gateway (forwards to gateway Envoy pods on port 8443)

```json
{
  "GatewayChecks": {
    "appmesh.describe-mesh.prod-checkout-mesh": {"egress_filter": "DROP_ALL"},
    "acm.describe-certificate.abc123": {"Status": "ISSUED"},
    "elbv2.describe-target-groups.tg-ingress-gateway": {"exists": true, "target_type": "instance"},
    "appmesh.describe-virtual-service.checkout.prod-checkout-mesh.svc.cluster.local": {"exists": true},
    "caller_iam": {
      "role": "AWSAppMeshDeployerRole",
      "permissions": ["appmesh:CreateVirtualGateway", "CreateGatewayRoute"]
    }
  }
}
```
