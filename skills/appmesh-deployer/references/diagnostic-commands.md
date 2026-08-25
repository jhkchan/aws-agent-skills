# App Mesh Diagnostic and Pre-flight Commands (load on demand)

Live-account pre-flight checks and post-deployment verification commands, moved verbatim from SKILL.md.


## Live-account pre-flight checks (skip if doing offline architecture plan)

**Live-account pre-flight checks (skip if doing offline architecture plan):**
1. Verify IAM permissions for `appmesh:CreateMesh`,
   `CreateVirtualNode`, `CreateVirtualRouter`, `CreateRoute`,
   `CreateVirtualGateway`, `CreateGatewayRoute`,
   `CreateVirtualService`, and `servicediscovery:CreateService`.
2. Verify the Cloud Map namespace exists:
   `aws servicediscovery list-namespaces --output table`.
   Capture the namespace ID — virtual nodes reference it.
3. For mTLS, verify the ACM Private CA exists and is ACTIVE:
   `aws acm-pca list-certificate-authorities --output table`.
4. For virtual gateway, verify the ALB/NLB listener forwards to the
   gateway's target group (the gateway's Envoy pods).
5. For EKS sidecar injection, verify the App Mesh Controller is
   installed: `kubectl get pods -n appmesh-system`.
6. For EKS namespace injection, verify the namespace is labeled:
   `kubectl get namespace <ns> --show-labels` —
   `appmesh.k8s.aws/sidecarInjectorWebhook=enabled`.

## Step 4: Post-verification — COMPLETED-equivalent check

After the deploy commands, run:
1. `describe-mesh --mesh-name <name>` returns the mesh with expected
   `egress_filter`.
2. `list-virtual-nodes --mesh-name <name>` returns all expected
   nodes.
3. `list-routes --mesh-name <name> --virtual-router-name <router>`
   returns routes with the expected weighted targets.
4. `describe-route` on a route returns the expected retry/timeout
   policy.
5. `list-virtual-gateways --mesh-name <name>` (if gateway) returns
   the gateway with expected listeners.
6. For EKS: `kubectl get pods -n <ns>` shows Envoy sidecar injected
   (2/2 containers in READY column).
7. For mTLS: `kubectl exec -it <pod> -c envoy -- curl -s localhost:9901/listeners`
   shows the listener with `tls_context` populated.
