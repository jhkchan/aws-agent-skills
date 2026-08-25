# Error Handling (load on demand) — App Mesh Virtual Service Deployer

Error-handling deep dives moved verbatim from SKILL.md. Loaded on demand.

---

## Error handling (moved from SKILL.md)

### Virtual service returns 503 (no healthy upstream)
- The virtual node has no backends. If using Cloud Map, verify
  instances are registered. If using DNS, verify the hostname
  resolves. Check health check configuration — failing health checks
  eject all endpoints.

### Canary traffic not splitting (all traffic to one node)
- The virtual service is backed by a virtual node, not a virtual
  router. Re-create the virtual service with a virtual router
  provider. Weighted routing requires the router.

### Envoy not injected (EKS)
- The namespace is not labeled for injection. Run
  `kubectl label namespace <ns> mesh=<mesh-name> appmesh=enabled`.
  Verify the App Mesh Controller is running in appmesh-system
  namespace.

### mTLS connections rejected (STRICT mode)
- Not all services have valid certificates. Switch to PERMISSIVE
  mode, issue certificates via ACM Private CA for all virtual nodes,
  verify SDS is distributing certs, then switch back to STRICT.

### DROP_ALL egress filter breaks database connectivity
- The mesh blocks all non-mesh egress. Create a virtual service for
  the database endpoint (with a virtual node using DNS discovery
  pointing to the database hostname), or switch to ALLOW_ALL egress.

### Cloud Map service has no instances
- Instances are not self-registering. For ECS, verify the task has
  Cloud Map service registration enabled. For EC2, verify the
  instance runs the Cloud Map registration agent. For EKS, verify
  the App Mesh Controller registers pods to Cloud Map.
