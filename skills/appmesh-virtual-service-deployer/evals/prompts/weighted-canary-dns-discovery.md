# Eval: weighted-canary-dns-discovery

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — virtual router with weighted HTTP route (90/10 split), DNS service discovery on both virtual nodes, virtual service backed by virtual router, retry and timeout policies

## Prompt

Create an App Mesh virtual service checkout.mesh.local in
mesh production-mesh (us-east-1). Two virtual nodes:
checkout-v1 and checkout-v2, both with DNS service discovery
(checkout-v1.default.svc.cluster.local and
checkout-v2.default.svc.cluster.local, port 8080 http).
Virtual router checkout-router with weighted HTTP route:
checkout-v1 (90%), checkout-v2 (10%) — canary. Retry policy
maxRetries=3. Timeout 15s. Egress ALLOW_ALL. Author account
123456789012.
