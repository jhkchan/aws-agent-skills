# Service Discovery and Routing — App Mesh Virtual Service Deployer

Deep reference on virtual node service discovery (DNS vs Cloud Map,
trade-offs, configuration), virtual router weighted route configuration
(HTTP/TCP/gRPC routes for canary/blue-green), retry and timeout
policies, circuit breaker and outlier detection, and traffic shifting
mechanics. Loaded on demand by the skill — kept out of the main
SKILL.md body so the provisioning procedure stays scannable.

## Service discovery

### DNS service discovery

DNS service discovery uses a DNS hostname for the virtual node's
backend resolution. Envoy resolves the hostname at runtime to obtain
the list of backend IPs.

```json
"serviceDiscovery": {
  "dns": {
    "hostname": "checkout.default.svc.cluster.local"
  }
}
```

**How it works:**
1. Envoy starts and resolves the DNS hostname.
2. DNS returns one or more IP addresses (A/AAAA records).
3. Envoy load-balances across the resolved IPs.
4. Envoy periodically re-resolves the hostname (respecting DNS TTL).
5. If DNS changes (new IPs), Envoy picks up the change on re-resolution.

**Best for:**
- Services with stable IPs (EC2 instances, fixed ECS tasks).
- ALB/NLB fronted services (DNS resolves to the load balancer).
- Services that already have a DNS name.

**Limitations:**
- DNS caching causes stale backends. If an IP is removed but DNS
  cache still returns it, Envoy sends traffic to a dead backend.
- TTL controls staleness: low TTL = fresher but more DNS queries;
  high TTL = fewer queries but more stale.
- No instance-level health checking (Envoy checks endpoint health
  but DNS does not report instance health).

**When NOT to use DNS:**
- ECS tasks that scale dynamically (use Cloud Map for auto-registration).
- EKS pods with frequent IP changes (use Cloud Map or the App Mesh
  Controller's built-in pod registration).

### Cloud Map service discovery

Cloud Map service discovery uses AWS Cloud Map for backend resolution.
Instances self-register with Cloud Map, and Envoy queries Cloud Map
for live backends.

```json
"serviceDiscovery": {
  "awsCloudMap": {
    "namespaceName": "mesh-services",
    "serviceName": "checkout"
  }
}
```

**How it works:**
1. A Cloud Map namespace and service are created beforehand.
2. Service instances self-register with Cloud Map on startup
   (ECS task networking auto-registers, EKS App Mesh Controller
   registers pods, EC2 instances use the Cloud Map agent).
3. Envoy queries the Cloud Map API for instances of the service.
4. Cloud Map returns only registered (live) instances.
5. Instances deregister on shutdown (or are removed by health checks).
6. Envoy load-balances across the Cloud Map-registered instances.

**Best for:**
- ECS tasks (auto-registration via ECS service discovery integration).
- EKS pods (auto-registration via App Mesh Controller).
- EC2 Auto Scaling groups (via Cloud Map instance registration).

**Advantages over DNS:**
- Near-real-time endpoint changes (no DNS cache lag).
- Instance-level health checking (Cloud Map health checks remove
  unhealthy instances).
- No DNS resolution overhead per request.

**Requirements:**
- Cloud Map namespace must exist BEFORE creating the virtual node.
- Cloud Map service must exist BEFORE creating the virtual node.
- Instances must be registered (ECS/EKS auto-register; EC2 needs
  the agent).

### Creating Cloud Map namespace and service

```bash
# Create an HTTP namespace
NAMESPACE_ID=$(aws servicediscovery create-http-namespace \
  --name mesh-services \
  --query 'OperationId' --output text \
  --region us-east-1)

# Wait for the namespace to be created
aws servicediscovery get-operation \
  --operation-id "$NAMESPACE_ID" \
  --query 'Operation.Status' --region us-east-1

# Create a service in the namespace
aws servicediscovery create-service \
  --name checkout \
  --namespace-id <namespace-id> \
  --dns-config '{"RoutingPolicy":"MULTIVALUE","DnsRecords":[{"Type":"A","TTL":10}]}' \
  --health-check-custom-config '{"FailureThreshold":1}' \
  --region us-east-1
```

## Virtual routers and weighted routes

### Virtual router anatomy

A virtual router holds listeners and route definitions. It is the
mechanism for traffic splitting (canary, blue-green).

```bash
aws appmesh create-virtual-router \
  --mesh-name production-mesh \
  --virtual-router-name checkout-router \
  --listeners '[{"portMapping":{"port":8080,"protocol":"http"}}]' \
  --region us-east-1
```

### HTTP weighted route (canary)

```bash
aws appmesh create-route \
  --mesh-name production-mesh \
  --virtual-router-name checkout-router \
  --route-name checkout-canary \
  --spec '{
    "httpRoute": {
      "match": {"prefix": "/"},
      "action": {
        "weightedTargets": [
          {"virtualNode": "checkout-v1", "weight": 90},
          {"virtualNode": "checkout-v2", "weight": 10}
        ]
      }
    }
  }' \
  --region us-east-1
```

### TCP weighted route

```json
"tcpRoute": {
  "action": {
    "weightedTargets": [
      {"virtualNode": "db-v1", "weight": 100},
      {"virtualNode": "db-v2", "weight": 0}
    ]
  }
}
```

### gRPC weighted route

```json
"grpcRoute": {
  "match": {"serviceName": "checkout.CheckoutService"},
  "action": {
    "weightedTargets": [
      {"virtualNode": "checkout-v1", "weight": 50},
      {"virtualNode": "checkout-v2", "weight": 50}
    ]
  }
}
```

### Updating route weights (canary progression)

```bash
# Shift canary from 10% to 50%
aws appmesh update-route \
  --mesh-name production-mesh \
  --virtual-router-name checkout-router \
  --route-name checkout-canary \
  --spec '{
    "httpRoute": {
      "match": {"prefix": "/"},
      "action": {
        "weightedTargets": [
          {"virtualNode": "checkout-v1", "weight": 50},
          {"virtualNode": "checkout-v2", "weight": 50}
        ]
      }
    }
  }' \
  --region us-east-1

# Complete the canary (100% to v2)
aws appmesh update-route \
  --mesh-name production-mesh \
  --virtual-router-name checkout-router \
  --route-name checkout-canary \
  --spec '{
    "httpRoute": {
      "match": {"prefix": "/"},
      "action": {
        "weightedTargets": [
          {"virtualNode": "checkout-v1", "weight": 0},
          {"virtualNode": "checkout-v2", "weight": 100}
        ]
      }
    }
  }' \
  --region us-east-1
```

**Critical:** route updates are pushed via xDS within seconds. No pod
restart needed.

## Retry and timeout policies

### Route-level retry

```json
"httpRoute": {
  "retryPolicy": {
    "httpRetryEvents": ["server-error", "gateway-error"],
    "tcpRetryEvents": ["connection-error"],
    "maxRetries": 3,
    "perRetryTimeout": {"unit": "ms", "value": 2000}
  }
}
```

**Retry event types:**
- `server-error` — HTTP 5xx responses
- `gateway-error` — 502, 503, 504 responses
- `client-error` — HTTP 4xx (unusual to retry)
- `stream-error` — retry on reset stream
- `connection-error` (TCP) — connection failure

### Route-level timeout

```json
"httpRoute": {
  "timeout": {
    "request": {"unit": "s", "value": 15},
    "idle": {"unit": "s", "value": 60}
  }
}
```

**Timeout types:**
- `request` — per-request timeout (time to receive a full response)
- `idle` — idle timeout (no data for this duration closes the connection)

## Circuit breaker and outlier detection

### Virtual node health check

```json
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
```

### Outlier detection (ejecting unhealthy endpoints)

```json
"listeners": [{
  "portMapping": {"port": 8080, "protocol": "http"},
  "outlierDetection": {
    "maxServerErrors": 5,
    "interval": {"unit": "s", "value": 10},
    "baseEjectionDuration": {"unit": "s", "value": 30},
    "maxEjectionPercent": 50
  }
}]
```

**Parameters:**
- `maxServerErrors` — consecutive 5xx errors before ejection
- `interval` — how often to evaluate ejection
- `baseEjectionDuration` — minimum ejection time
- `maxEjectionPercent` — max percent of endpoints that can be ejected

## Terraform example

```hcl
resource "aws_appmesh_mesh" "main" {
  name = "production-mesh"
  spec {
    egress_filter { type = "ALLOW_ALL" }
  }
}

resource "aws_appmesh_virtual_node" "checkout_v1" {
  name      = "checkout-v1"
  mesh_name = aws_appmesh_mesh.main.id
  spec {
    listener {
      port_mapping {
        port     = 8080
        protocol = "http"
      }
    }
    service_discovery {
      dns { hostname = "checkout-v1.default.svc.cluster.local" }
    }
  }
}

resource "aws_appmesh_virtual_node" "checkout_v2" {
  name      = "checkout-v2"
  mesh_name = aws_appmesh_mesh.main.id
  spec {
    listener {
      port_mapping {
        port     = 8080
        protocol = "http"
      }
    }
    service_discovery {
      dns { hostname = "checkout-v2.default.svc.cluster.local" }
    }
  }
}

resource "aws_appmesh_virtual_router" "checkout" {
  name      = "checkout-router"
  mesh_name = aws_appmesh_mesh.main.id
  listener {
    port_mapping {
      port     = 8080
      protocol = "http"
    }
  }
}

resource "aws_appmesh_route" "canary" {
  name                = "checkout-canary"
  mesh_name           = aws_appmesh_mesh.main.id
  virtual_router_name = aws_appmesh_virtual_router.checkout.name
  spec {
    http_route {
      match { prefix = "/" }
      action {
        weighted_target {
          virtual_node = aws_appmesh_virtual_node.checkout_v1.name
          weight       = 90
        }
        weighted_target {
          virtual_node = aws_appmesh_virtual_node.checkout_v2.name
          weight       = 10
        }
      }
    }
  }
}

resource "aws_appmesh_virtual_service" "checkout" {
  name      = "checkout.mesh.local"
  mesh_name = aws_appmesh_mesh.main.id
  spec {
    provider {
      virtual_router {
        virtual_router_name = aws_appmesh_virtual_router.checkout.name
      }
    }
  }
}
```

## Common routing pitfalls

1. **Virtual service backed by virtual node (no router).** Cannot do
   weighted splitting. Re-create with a virtual router provider.

2. **Route weights sum to non-100.** Weights are normalized, so 3:1
   (75%:25%) and 90:10 both work. But conventionally use 100 for
   clarity.

3. **DNS hostname not resolvable by Envoy.** Envoy resolves the
   hostname at runtime. If DNS is misconfigured, Envoy has no backends.
   Verify with `dig` or `nslookup` from inside the pod.

4. **Cloud Map service has no instances.** Instances must self-register.
   Without registration, the virtual node has no backends and returns
   503.

5. **gRPC route match missing serviceName.** gRPC routes require a
   `serviceName` match (the gRPC service fully-qualified name). Without
   it, the route does not match any gRPC calls.
