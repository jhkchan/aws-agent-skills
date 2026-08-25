# Advanced Patterns (load on demand) — App Mesh Virtual Service Deployer

Edge-case catalogs, expert-knowledge deep dives, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

---

## Cross-dependency gotchas (moved from SKILL.md)

- The virtual service DNS name (e.g., `service.mesh.local`) must
  match what clients call. If clients call `service.namespace.svc
  .cluster.local`, the virtual service must use that exact hostname.
- Cloud Map service discovery requires instances to self-register.
  If the Cloud Map service has no instances, the virtual node has no
  backends and traffic returns 503.
- The App Mesh Controller on EKS must be installed BEFORE labeling
  namespaces for injection. Labeling without the controller does
  nothing.
- mTLS STRICT mode on a virtual node rejects all connections that
  lack a valid client certificate. Start with PERMISSIVE mode during
  migration, then switch to STRICT.
- The egress filter on the mesh (DROP_ALL vs ALLOW_ALL) controls
  whether pods can talk to non-mesh services. DROP_ALL blocks all
  egress not explicitly allowed — plan for this or use ALLOW_ALL.

---

## Step 13 — Recent features (moved from SKILL.md)

**Recent AWS features (2023-2026):**

- **App Mesh Gateway Controller for EKS (2023-2024):** A CRD-based
  controller that allows declaring virtual gateways and gateway
  routes as Kubernetes resources, simplifying ingress configuration.

- **mTLS via SDS enhancement (2024-2025):** Improved Secret Discovery
  Service integration, allowing Envoy to fetch certificates from
  external SDS backends (not just Kubernetes secrets), enabling
  tighter integration with cert-manager and external CA systems.

- **Outlier detection improvements (2024-2025):** Enhanced outlier
  detection with configurable failure percentage thresholds and
  consecutive failure gating, giving finer control over endpoint
  ejection behavior.

- **App Mesh multi-cluster mesh (2025-2026):** Cross-cluster mesh
  connectivity via Cloud Map multi-cluster service discovery, allowing
  virtual nodes to span EKS clusters in different regions.

- **Envoy version upgrades (2025-2026):** App Mesh Envoy images
  updated to Envoy 1.30+ with improved HTTP/3 support and QUIC
  transport for mesh-internal traffic.
