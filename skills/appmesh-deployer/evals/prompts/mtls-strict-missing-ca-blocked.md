# Eval prompt: mtls-strict-missing-ca-blocked

User requests STRICT mTLS for east-west traffic hardening. Plan the
operation and emit the standard VERDICT block.

Operation: deploy-mtls
Mesh: prod-secure-mesh (already exists)
Region: us-east-1
mTLS mode: STRICT
Cert distribution: SDS (Secret Discovery Service)
CA: (user did not specify; expects skill to identify missing)

```json
{
  "mTLSChecks": {
    "appmesh.describe-mesh.prod-secure-mesh": {"exists": true, "egress_filter": "DROP_ALL"},
    "acm-pca.list-certificate-authorities": {"certificateAuthorities": []},
    "servicediscovery.list-namespaces": {
      "prod-secure-internal": {"error": "namespace not found"}
    },
    "eks_namespace_label.secure": {"labeled": true}
  }
}
```
