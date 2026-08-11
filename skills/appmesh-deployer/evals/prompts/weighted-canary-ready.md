# Eval prompt: weighted-canary-ready

Plan the following App Mesh deployment and emit the standard VERDICT
block (MESH_SPEC, VERDICT, ARCHITECTURE, CHECKLIST, FINDINGS,
DEPLOY_COMMANDS).

Operation: deploy-mesh
Mesh name: prod-checkout-mesh
Region: us-east-1
Egress filter: DROP_ALL
Cloud Map namespace: prod-internal (ID ns-abc123, DNS-based)
Virtual nodes:
  - checkout-service-v1 (Cloud Map service checkout-v1, HTTP listener port 8080, health check /health)
  - checkout-service-v2 (Cloud Map service checkout-v2, HTTP listener port 8080, health check /health)
Virtual router: checkout-router on port 8080
Route: checkout-canary (HTTP prefix /), 90/10 weighted targets (v1/v2)
Retry: gateway-error + 5xx, maxRetries 3, perRetryTimeoutMillis 2000
Timeout: requestTimeoutMillis 5000, idleTimeoutMillis 300000
Compute: EKS namespace prod labeled appmesh.k8s.aws/sidecarInjectorWebhook=enabled

```json
{
  "NamespaceCheck": {
    "servicediscovery.list-namespaces": {
      "prod-internal": {"id": "ns-abc123", "type": "DNS", "status": "ACTIVE"}
    },
    "appmesh.describe-mesh.prod-checkout-mesh": {
      "error": "NotFoundException",
      "status": "mesh does not exist yet"
    },
    "caller_iam": {
      "role": "AWSAppMeshDeployerRole",
      "permissions": ["appmesh:CreateMesh", "CreateVirtualNode", "CreateVirtualRouter", "CreateRoute"]
    },
    "eks_namespace_label": {"namespace": "prod", "labeled": true}
  },
  "ExistingMesh": null
}
```
