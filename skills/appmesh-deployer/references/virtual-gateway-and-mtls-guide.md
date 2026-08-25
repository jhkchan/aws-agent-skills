# Virtual Gateway and mTLS Reference

Load this reference when planning or executing any virtual gateway or
mutual TLS configuration. The procedures below cover ingress from
outside the mesh and east-west traffic hardening.

## Decision tree — ingress path

| Scenario | Use | Why |
|---|---|---|
| Public HTTPS ingress with mesh policies (retry, timeout, mTLS) | **Virtual gateway + ALB** | ALB terminates TLS; gateway Envoy applies mesh policies |
| Internal ingress from another VPC | **Virtual gateway + NLB** | NLB for TCP passthrough; gateway terminates mTLS |
| API Gateway → mesh | **API Gateway → Virtual gateway** | API Gateway for auth/rate-limit; gateway for mesh routing |
| Direct ALB → mesh member pods | **NOT recommended** | Bypasses Envoy; no mesh policies (retry, timeout, mTLS) |
| Legacy CLB → mesh | **Migrate to ALB + virtual gateway first** | CLB has no target group support |

## Virtual gateway procedure

**When to use:** north-south ingress from outside the mesh into mesh
members with mesh policies applied.

**Pre-checks:**
1. Mesh exists with `egress_filter` set.
2. ALB/NLB listener forwards to the gateway target group.
3. Gateway target group references the gateway's Envoy pods (port
   8443 for HTTPS, 8080 for HTTP).
4. ACM certificate ARN exists (for HTTPS gateway listener).
5. Caller IAM role holds `appmesh:CreateVirtualGateway`,
   `CreateGatewayRoute`.

**Command sequence:**
```bash
# 1. Create the virtual gateway
aws appmesh create-virtual-gateway \
  --mesh-name prod-checkout-mesh \
  --virtual-gateway-name ingress-gateway \
  --spec '{
    "listeners": [{
      "portMapping": {"port": 8443, "protocol": "http"},
      "tls": {
        "certificate": {"acm": {"certificateArn": "arn:aws:acm:us-east-1:111111111111:certificate/abc123"}},
        "mode": "PERMISSIVE"
      },
      "healthCheck": {
        "protocol": "http",
        "path": "/health",
        "healthyThreshold": 2,
        "unhealthyThreshold": 2,
        "timeoutMillis": 2000,
        "intervalMillis": 5000
      }
    }],
    "logging": {"accessLog": {"file": {"path": "/dev/stdout"}}}
  }'

# 2. Create gateway routes (weighted to virtual services)
aws appmesh create-gateway-route \
  --mesh-name prod-checkout-mesh \
  --virtual-gateway-name ingress-gateway \
  --gateway-route-name checkout-ingress \
  --spec '{
    "httpRoute": {
      "match": {"prefix": "/checkout"},
      "action": {
        "target": {"virtualService": {"virtualServiceName": "checkout.prod-checkout-mesh.svc.cluster.local"}}
      }
    }
  }'
```

**Post-verification:**
```bash
aws appmesh describe-virtual-gateway --mesh-name prod-checkout-mesh --virtual-gateway-name ingress-gateway
aws appmesh list-gateway-routes --mesh-name prod-checkout-mesh --virtual-gateway-name ingress-gateway
# Verify ALB target group health checks pass for gateway pods
kubectl get pods -n prod -l app.kubernetes.io/name=ingress-gateway
```

## mTLS procedure

**When to use:** east-west traffic hardening within the mesh.

**Modes:**
- **STRICT**: rejects clients without a valid cert (or with an
  untrusted CA). Use after cert distribution is verified.
- **PERMISSIVE**: accepts both mTLS and plaintext. Use during
  migration to verify cert distribution before enforcing STRICT.

**Pre-checks:**
1. ACM Private CA ARN exists with `Status: ACTIVE`.
2. SDS (Secret Discovery Service) backend configured on Envoy.
3. Cert chain references the same CA across all mesh members
   (mixed CAs = asymmetric trust = STRICT fails).
4. Listener protocol is `http` or `grpc` (TCP does not support mTLS).

**Command sequence (update virtual node listener for mTLS):**
```bash
aws appmesh update-virtual-node \
  --mesh-name prod-checkout-mesh \
  --virtual-node-name checkout-service-v1 \
  --spec '{
    "serviceDiscovery": {"cloudMap": {"namespaceName": "prod-internal", "serviceName": "checkout-v1"}},
    "listeners": [{
      "portMapping": {"port": 8080, "protocol": "http"},
      "tls": {
        "certificate": {"sds": {"secretName": "checkout-cert"}},
        "mode": "STRICT",
        "validation": {
          "trust": {"sds": {"secretName": "checkout-ca-bundle"}}
        }
      }
    }]
  }'
```

**Migration to STRICT (recommended sequence):**
1. Deploy ACM Private CA (verify `Status: ACTIVE`).
2. Configure SDS backend on Envoy (Secret Discovery Service).
3. Set listener `mode: PERMISSIVE` on all mesh members.
4. Verify cert distribution via `kubectl exec -it <pod> -c envoy --
   curl -s localhost:9901/listeners` — `tls_context` populated.
5. Observe mTLS handshake success rate in Envoy metrics
   (`envoy_tls_inspector_*`).
6. Switch listener `mode: STRICT` on one node; observe 5xx rate.
7. Roll STRICT across all nodes; verify east-west traffic encrypted.

## Common gateway misconfigurations

1. **ALB → mesh member pods directly** (bypassing gateway): no mesh
   policies applied. Fix: route ALB → gateway target group → gateway
   pods → mesh members.

2. **Gateway target group references service pods (not gateway
   pods):** mesh policies apply only to traffic flowing through the
   gateway Envoy. The service pods are not the gateway; target the
   gateway's Envoy pods.

3. **mTLS mode STRICT before SDS configured:** all handshakes fail
   → outage. Always start in PERMISSIVE and verify cert distribution.

4. **Mixed CAs across mesh members:** STRICT mTLS requires symmetric
   trust — every member's cert must be signed by the CA trusted by
   the listener. Mixed CAs = asymmetric trust = STRICT fails.

5. **Gateway listener protocol mismatch:** HTTPS ALB listener must
   forward to a gateway listener configured for HTTPS (with ACM
   cert) or HTTP (with TLS terminated at ALB). Mismatch = TLS errors
   at the gateway.

## CLI boilerplate (moved from SKILL.md)

### Create a virtual gateway for ingress

```bash
aws appmesh create-virtual-gateway \
  --mesh-name "prod-checkout-mesh" \
  --virtual-gateway-name "ingress-gateway" \
  --spec '{
    "listeners": [{
      "portMapping": {"port": 8443, "protocol": "http"},
      "tls": {
        "certificate": {"acm": {"certificateArn": "arn:aws:acm:us-east-1:111111111111:certificate/abc123"}},
        "mode": "PERMISSIVE"
      }
    }]
  }'

aws appmesh create-gateway-route \
  --mesh-name "prod-checkout-mesh" \
  --virtual-gateway-name "ingress-gateway" \
  --gateway-route-name "checkout-ingress" \
  --spec '{
    "httpRoute": {
      "match": {"prefix": "/checkout"},
      "action": {
        "target": {"virtualService": {"virtualServiceName": "checkout.prod-checkout-mesh.svc.cluster.local"}}
      }
    }
  }'
```

### Enable mutual TLS on a listener

```bash
aws appmesh update-virtual-node \
  --mesh-name "prod-checkout-mesh" \
  --virtual-node-name "checkout-service-v1" \
  --spec '{
    "serviceDiscovery": {"cloudMap": {"namespaceName": "prod-internal", "serviceName": "checkout-v1"}},
    "listeners": [{
      "portMapping": {"port": 8080, "protocol": "http"},
      "tls": {
        "certificate": {"sds": {"secretName": "checkout-cert"}},
        "mode": "STRICT",
        "validation": {
          "trust": {"sds": {"secretName": "checkout-ca-bundle"}}
        }
      }
    }]
  }'
```

`mode: STRICT` rejects clients without a valid cert; `PERMISSIVE`
allows both mTLS and plaintext during migration. SDS (Secret
Discovery Service) is the recommended cert distribution mechanism.

