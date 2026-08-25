# Worked Examples (load on demand) — App Mesh Virtual Service Deployer

Secondary worked examples and full command payloads, moved verbatim from SKILL.md. Loaded on demand.

---

## Step 5 — Circuit breaker and outlier detection (moved from SKILL.md)

Circuit breaking is configured via virtual node backend defaults
(connection pool limits) and outlier detection (ejecting unhealthy
endpoints).

**Virtual node with circuit breaker:**

```bash
aws appmesh create-virtual-node \
  --mesh-name production-mesh \
  --virtual-node-name checkout-v1 \
  --spec '{
    "serviceDiscovery": {
      "awsCloudMap": {
        "namespaceName": "mesh-services",
        "serviceName": "checkout"
      }
    },
    "listeners": [{
      "portMapping": {"port": 8080, "protocol": "http"}
    }],
    "backendDefaults": {
      "clientPolicy": {
        "healthCheck": {
          "protocol": "http",
          "path": "/health",
          "healthyThreshold": 2,
          "unhealthyThreshold": 3,
          "timeoutMillis": 2000,
          "intervalMillis": 5000
        }
      }
    }
  }' \
  --region us-east-1
```

**Outlier detection** (ejecting unhealthy endpoints):

```json
"outlierDetection": {
  "maxServerErrors": 5,
  "interval": {"unit": "s", "value": 10},
  "baseEjectionDuration": {"unit": "s", "value": 30},
  "maxEjectionPercent": 50
}
```

---

## Step 7 — Virtual gateway (north-south ingress) (moved from SKILL.md)

A virtual gateway allows external traffic to enter the mesh.

**Create a virtual gateway:**

```bash
aws appmesh create-virtual-gateway \
  --mesh-name production-mesh \
  --virtual-gateway-name ingress-gateway \
  --spec '{
    "listeners": [{
      "portMapping": {"port": 8080, "protocol": "http"},
      "healthCheck": {
        "protocol": "http",
        "path": "/health",
        "healthyThreshold": 2,
        "unhealthyThreshold": 2,
        "timeoutMillis": 2000,
        "intervalMillis": 5000
      }
    }]
  }' \
  --region us-east-1
```

**Create a gateway route:**

```bash
aws appmesh create-gateway-route \
  --mesh-name production-mesh \
  --virtual-gateway-name ingress-gateway \
  --gateway-route-name checkout-ingress \
  --spec '{
    "httpRoute": {
      "action": {
        "target": {
          "virtualService": {
            "virtualServiceName": "checkout.mesh.local"
          }
        }
      },
      "match": {"prefix": "/checkout"}
    }
  }' \
  --region us-east-1
```

External traffic enters via the virtual gateway (fronted by ALB/NLB),
follows the gateway route to the virtual service, which routes through
the virtual router to the appropriate virtual node.

---

## Step 10 — Observability (CloudWatch + X-Ray) (moved from SKILL.md)

App Mesh integrates with CloudWatch metrics and X-Ray tracing.

**Enable X-Ray tracing (virtual node listener):**

```json
"listeners": [{
  "portMapping": {"port": 8080, "protocol": "http"},
  "healthCheck": {...},
  "accessLog": {
    "file": {"path": "/dev/stdout"}
  }
}]
```

**CloudWatch metrics** are automatically emitted by Envoy:
- `envoy_cluster_upstream_rq_total` — request count
- `envoy_cluster_upstream_rq_2xx` — successful responses
- `envoy_cluster_upstream_rq_5xx` — server errors
- `envoy_cluster_upstream_rq_time` — latency distribution

**X-Ray tracing** requires the X-Ray daemon sidecar (EKS) or the
X-Ray integration in the Envoy configuration.
