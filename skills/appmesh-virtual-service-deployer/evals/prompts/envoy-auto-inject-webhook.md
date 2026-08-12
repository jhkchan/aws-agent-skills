# Eval: envoy-auto-inject-webhook

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — App Mesh Controller installed via Helm, namespace labeled for injection, mutating webhook auto-injects Envoy sidecar

## Prompt

Set up App Mesh on an EKS cluster for the default namespace.
Mesh production-mesh. Install App Mesh Controller via Helm in
appmesh-system namespace. Label namespace default for auto-
injection (mesh=production-mesh, appmesh=enabled). Virtual node
api-v1 with DNS discovery api.default.svc.cluster.local port
8080. Region us-east-1. Account 123456789012.
