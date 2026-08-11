# Eval prompt: allow-all-egress-warning-ready

User requests ALLOW_ALL egress filter for a dev mesh. Plan the
operation and emit the standard VERDICT block — must surface ALLOW_ALL
as a WARN finding with DROP_ALL as the recommended production posture.

Operation: deploy-mesh
Mesh name: dev-test-mesh
Region: us-east-1
Egress filter: ALLOW_ALL
Virtual nodes: api-service-v1 (Cloud Map service api-v1, HTTP listener port 8080)
Virtual router: api-router on port 8080
Route: api-default (HTTP prefix /), 100/0 weighted targets (v1 only)
Compute: EKS namespace dev labeled for sidecar injection

```json
{
  "DevMeshChecks": {
    "servicediscovery.list-namespaces": {
      "dev-internal": {"id": "ns-dev123", "type": "DNS", "status": "ACTIVE"}
    },
    "appmesh.describe-mesh.dev-test-mesh": {"error": "NotFoundException"},
    "eks_namespace_label.dev": {"labeled": true},
    "caller_iam": {
      "role": "AWSAppMeshDeployerRole",
      "permissions": ["appmesh:CreateMesh", "CreateVirtualNode", "CreateVirtualRouter", "CreateRoute"]
    }
  }
}
```
