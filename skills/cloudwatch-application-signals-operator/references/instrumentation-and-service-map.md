# Instrumentation and Service Map — CloudWatch Application Signals Operator

Deep reference on OTel instrumentation (SDK and auto-instrumentation),
service auto-discovery, service map visualization, CloudWatch RUM
integration, X-Ray trace correlation, service hierarchy, and
multi-service observability. Loaded on demand by the skill — kept out
of the main SKILL.md body so the operation procedure stays scannable.

## OTel SDK instrumentation

### Python

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# Initialize tracer provider
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Export to CloudWatch via OTLP
exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
processor = BatchSpanProcessor(exporter)
trace.get_tracer_provider().add_span_processor(processor)

# Auto-instrument Flask and requests
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()
```

### Java

```java
// Add OTel SDK + agent
// JVM flag: -javaagent:opentelemetry-javaagent.jar
// The agent auto-instruments supported frameworks (Spring, etc.)

// Manual span creation
import io.opentelemetry.api.trace.Tracer;
import io.opentelemetry.api.GlobalOpenTelemetry;

Tracer tracer = GlobalOpenTelemetry.getTracer("payments-api");
Span span = tracer.spanBuilder("processPayment").startSpan();
try (Scope scope = span.makeCurrent()) {
    // Business logic
} finally {
    span.end();
}
```

### Node.js

```javascript
const { trace, context } = require('@opentelemetry/api');
const { NodeTracerProvider } = require('@opentelemetry/sdk-trace-node');
const { BatchSpanProcessor } = require('@opentelemetry/sdk-trace-base');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-otlp-grpc');
const { AutoInstrumentation } = require('@opentelemetry/auto-instrumentations-node');

const provider = new NodeTracerProvider();
const exporter = new OTLPTraceExporter({ url: 'http://localhost:4317' });
provider.addSpanProcessor(new BatchSpanProcessor(exporter));
provider.register();

// Auto-instrument Express, HTTP, etc.
new AutoInstrumentation().instrument();
```

### Span attributes for Application Signals

Application Signals requires specific span attributes to discover
services and derive SLIs:

| Attribute | Description | Required |
|---|---|---|
| `service.name` | Name of the service | Yes |
| `operation.name` | Name of the operation | Yes |
| `http.method` | HTTP method (GET, POST, etc.) | For HTTP |
| `http.status_code` | HTTP response status | For HTTP |
| `rpc.system` | RPC system (grpc, etc.) | For RPC |

The OTel auto-instrumentation libraries set these automatically for
supported frameworks (Flask, Express, Spring, etc.).

## CloudWatch Agent auto-instrumentation

For environments where code changes are not possible, the CloudWatch
Agent can auto-instrument applications:

### EC2

```bash
# Install CloudWatch Agent with OTel support
sudo yum install amazon-cloudwatch-agent

# Configure for Application Signals
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -c ssm:AmazonCloudWatch-ApplicationSignals \
  -s
```

### EKS / Kubernetes

```yaml
# CloudWatch Agent DaemonSet with OTel collector
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: cloudwatch-agent
spec:
  template:
    spec:
      containers:
        - name: cloudwatch-agent
          image: amazon/cloudwatch-agent:latest
          env:
            - name: ENABLE_APP_SIGNALS
              value: "true"
```

### ECS / Fargate

Add the CloudWatch Agent as a sidecar container with Application
Signals enabled in the task definition.

## Service auto-discovery

### Discovery flow

```text
1. Application emits OTel traces
   ↓
2. CloudWatch Agent collects traces via OTLP
   ↓
3. Traces sent to CloudWatch backend
   ↓
4. Application Signals processes traces
   ↓
5. Services extracted from service.name attribute
   ↓
6. Operations extracted from operation.name / HTTP method + path
   ↓
7. SLI metrics derived (availability, latency)
   ↓
8. Service map built from trace context propagation
   ↓
9. Services visible in Application Signals console (~15 min)
```

### Verifying discovery

```bash
# Check if Application Signals sees the service
aws cloudwatch list-metrics \
  --namespace AWS/ApplicationSignals \
  --query 'Metrics[*].Dimensions[?Name==`ServiceName`].Value | []' \
  --output table

# Check trace volume
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationSignals \
  --metric-name CallCount \
  --dimensions Name=ServiceName,Value=payments-api \
  --start-time 2026-08-11T00:00:00Z \
  --end-time 2026-08-11T23:59:59Z \
  --period 300 \
  --statistics Sum
```

## Service map visualization

### How the service map is built

The service map is derived from trace context propagation. When
service A calls service B, the trace context (W3C TraceContext header)
propagates from A to B. Application Signals uses this to build edges.

```text
Trace propagation:
  Client request → API Gateway
    traceparent: 00-<trace-id>-<span-id>-01
         ↓
  API Gateway → orders-api
    traceparent: 00-<trace-id>-<span-id>-01
         ↓
  orders-api → inventory-api
    traceparent: 00-<trace-id>-<span-id>-01
         ↓
  inventory-api → database

Service map built from propagation:
  Client → API Gateway → orders-api → inventory-api → database
                                    ↘ payments-api
```

### Color coding

| Color | Meaning |
|---|---|
| Green | Healthy (SLI within target) |
| Yellow | Degraded (SLI approaching warning threshold) |
| Red | Unhealthy (SLI breaching target) |
| Gray | Unknown (insufficient data) |

### W3C TraceContext propagation

For the service map to work, OTel trace context MUST propagate across
service boundaries:

```python
# Python — propagate trace context in HTTP calls
import requests
from opentelemetry.propagate import inject

headers = {}
inject(headers)  # Injects traceparent header
response = requests.get('http://inventory-api/items', headers=headers)
```

If trace context is NOT propagated, the service map shows disconnected
services with no edges.

## CloudWatch RUM integration

### RUM app monitor setup

```bash
aws rum create-app-monitor \
  --name storefront-rum \
  --domain storefront.example.com \
  --app-monitor-configuration '{
    "AllowCookies": true,
    "EnableXRay": true,
    "SessionSampleRate": 1.0,
    "Telemetries": ["errors", "performance", "http"]
  }'
```

### RUM + Application Signals correlation

When `EnableXRay: true`, RUM generates client-side traces with trace
IDs that are propagated to the backend. Application Signals correlates
these with server-side traces:

```text
Client-side (RUM):
  User clicks "Submit Order"
  RUM trace: client → browser → network

Server-side (Application Signals):
  API Gateway receives request (same trace ID)
  Application Signals trace: api-gateway → orders-api → payments-api

End-to-end correlation:
  RUM trace ID = Application Signals trace ID
  → Full waterfall: user click → browser → network → API → DB
```

### Embedding RUM in frontend

```javascript
// Include RUM script in HTML
const rumScript = document.createElement('script');
rumScript.src = 'https://client.rum.us-east-1.amazonaws.com/cwr.js';
document.head.appendChild(rumScript);

// Initialize
cwr('init', {
  sessionId: '...',
  version: '1.0',
  endpoint: 'https://dataplane.rum.us-east-1.amazonaws.com',
  telemetries: ['errors', 'performance', 'http'],
  enableXRay: true
});
```

## X-Ray trace correlation

### Application Signals vs X-Ray

| Feature | Application Signals | X-Ray |
|---|---|---|
| Abstraction level | High (SLOs, SLIs, service map) | Low (raw traces, service graph) |
| Auto-derived metrics | Yes (availability, latency SLIs) | No (manual insights) |
| SLO management | Yes (create, monitor, alert) | No |
| Trace detail | Summary | Full waterfall |
| Drill-down | From SLO → traces | Traces list → individual trace |

### Drill-down from Application Signals to X-Ray

```text
1. Application Signals shows SLO status (e.g., availability 99.7%)
2. Click on the breaching SLO → shows recent failed operations
3. Click on a failed operation → shows recent traces
4. Click on a trace → X-Ray trace waterfall view
5. Identify root cause from span-level detail (error, latency, annotations)
```

Both Application Signals and X-Ray read from the same trace data. The
difference is the abstraction level and the features built on top.

## Service hierarchy

### Service → Operation model

```text
Application Signals organizes telemetry as:

  Account
    └── Region
          └── Service: payments-api
                ├── Operation: POST /charge
                │     ├── SLI: availability (auto-derived)
                │     ├── SLI: latency (auto-derived)
                │     └── SLO: 99.9% availability (30-day)
                ├── Operation: GET /status
                │     ├── SLI: availability
                │     ├── SLI: latency
                │     └── SLO: 99.95% availability (30-day)
                └── Operation: POST /refund
                      ├── SLI: availability
                      ├── SLI: latency
                      └── SLO: 99.9% availability (30-day)

  Service-level SLI = weighted aggregate of all operations
```

### Operation-level vs service-level SLOs

```text
Service-level SLO:
  Covers ALL operations in the service
  Target is typically lower (e.g., 99.9%) since it aggregates all ops
  Good for: overall service health monitoring

Operation-level SLO:
  Covers a SINGLE operation
  Target can be tighter for critical operations (e.g., 99.99%)
  Good for: critical path monitoring (payments, auth, etc.)
```

## Multi-service observability

### Fleet dashboard

Create a CloudWatch dashboard aggregating SLO status across services:

```bash
aws cloudwatch put-dashboard \
  --dashboard-name "SLO-Fleet-Overview" \
  --dashboard-body '{
    "widgets": [
      {
        "type": "metric",
        "properties": {
          "metrics": [
            ["AWS/ApplicationSignals", "ErrorRate", "ServiceName", "orders-api"],
            ["AWS/ApplicationSignals", "ErrorRate", "ServiceName", "payments-api"],
            ["AWS/ApplicationSignals", "ErrorRate", "ServiceName", "shipping-api"]
          ],
          "period": 300,
          "stat": "Average",
          "region": "us-east-1",
          "title": "Error Rate by Service"
        }
      }
    ]
  }'
```

### Cross-account observability

For multi-account setups, use CloudWatch cross-account sharing:

```bash
# In each source account — share with monitoring account
aws cloudwatch put-account-policy \
  --policy-name "CrossAccountSharing" \
  --policy-type "CROSS_ACCOUNT" \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::MONITORING_ACCOUNT:root"},
      "Action": ["cloudwatch:GetMetricData", "cloudwatch:GetMetricStatistics"],
      "Resource": "*"
    }]
  }'
```

This allows the monitoring account to view Application Signals data
from all linked accounts in a single console view.
---

## Expert heuristic: service hierarchy and operation-level SLOs (moved from SKILL.md)

Application Signals organizes telemetry hierarchically:

```text
Service hierarchy:
  Service (e.g., "payments-api")
    ├── Operation: POST /charge
    ├── Operation: GET /status
    ├── Operation: POST /refund
    └── Operation: GET /health

SLOs can be defined at TWO levels:
  ├── Service-level SLO: covers ALL operations in the service
  │     e.g., "payments-api availability > 99.9%"
  └── Operation-level SLO: covers a SINGLE operation
        e.g., "POST /charge latency P99 < 500ms"
```

**Key implication:** for critical operations (e.g., payment processing),
define operation-level SLOs with tighter targets. For overall service
health, use service-level SLOs. Both types consume the same auto-derived
SLI metrics.
---

## Step 1 Option A: OTel SDK instrumentation (application-level) (moved from SKILL.md)

Instrument your application with the OpenTelemetry SDK:

```python
# Python example — add OTel SDK to your application
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Export to CloudWatch (via OTLP collector / CloudWatch Agent)
exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
span_processor = BatchSpanProcessor(exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Instrument HTTP handlers
@tracer.start_as_current_span("process_payment")
def process_payment(request):
    # Business logic
    pass
```
---

## Step 1 Option B: CloudWatch Agent auto-instrumentation (moved from SKILL.md)

The CloudWatch Agent with OTel auto-instrumentation can inject tracing
without code changes for supported runtimes:

```bash
# Install CloudWatch Agent with OTel on EC2/ECS/EKS
aws ssm create-association \
  --name AmazonCloudWatch-ManageAgent \
  --targets Key=InstanceIds,Values=i-1234567890abcdef0 \
  --parameters '{"action":["configure"],"mode":["ec2"],"configurationSource":["ssm"]}'

# The agent configuration enables OTel auto-instrumentation
```

**Key implication:** auto-instrumentation is faster to deploy (no code
changes) but provides less customization than SDK instrumentation. For
production, SDK instrumentation is recommended for fine-grained control.
---

## Step 7 — CloudWatch RUM integration (moved from SKILL.md)

CloudWatch RUM (Real User Monitoring) provides client-side telemetry.
Integrating RUM with Application Signals enables end-to-end
observability.

```bash
# Create a RUM app monitor
aws rum create-app-monitor \
  --name payments-frontend \
  --domain payments.example.com \
  --app-monitor-configuration '{
    "AllowCookies": true,
    "EnableXRay": true,
    "SessionSampleRate": 1.0,
    "Telemetries": ["errors", "performance", "http"]
  }'
```

**Key integration point:** `EnableXRay: true` correlates RUM client-side
traces with server-side X-Ray/Application Signals traces via shared
trace IDs. This provides end-to-end visibility from user click to
database query.
---

## Step 8 — X-Ray trace correlation (moved from SKILL.md)

Application Signals and X-Ray share trace data. Application Signals
provides higher-level abstractions; X-Ray provides raw trace detail.

```text
Application Signals → X-Ray correlation:
  1. Application Signals shows service-level SLI and SLO status
  2. Click on a failing service → drill-down to individual traces
  3. X-Ray trace view shows span-level detail (time, error, annotations)
  4. Identify root cause from trace waterfall

  The "Service Map" in Application Signals and the "Service Graph" in
  X-Ray are derived from the SAME trace data, but at different
  abstraction levels.
```
