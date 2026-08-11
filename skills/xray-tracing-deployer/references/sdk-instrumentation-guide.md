# SDK Instrumentation Guide — X-Ray Tracing Deployer

Deep reference on SDK instrumentation (Python, Node.js, Java, Go, .NET),
AWS SDK patching, annotation vs metadata, trace context propagation,
OpenTelemetry / ADOT migration, the full NEVER list, edge-case handling,
and pre-flight safety CLI.

## Python (Flask / Django)

### Install

```bash
pip install aws-xray-sdk
```

### Flask middleware

```python
from flask import Flask
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware

app = Flask(__name__)

# Configure the recorder
xray_recorder.configure(
    service="payments-api",
    sampling=False,  # Use central sampling rules from X-Ray API
    context_missing="LOG_ERROR",  # Don't crash if no segment context
)

# Apply middleware
app.wsgi_app = XRayMiddleware(app, xray_recorder)

# Patch AWS SDK + requests for downstream tracing
from aws_xray_sdk.core import patch_all
patch_all()  # patches botocore, requests, sqlite3, etc.
```

### Capture function calls

```python
from aws_xray_sdk.core import xray_recorder

@xray_recorder.capture("process_payment")
def process_payment(order_id):
    # Automatically wrapped in a subsegment named "process_payment"
    xray_recorder.put_annotation("order_id", order_id)
    xray_recorder.put_metadata("payment_method", "stripe")
    return charge_card(order_id)
```

### Django middleware

```python
# settings.py
MIDDLEWARE = [
    'aws_xray_sdk.ext.django.middleware.XRayMiddleware',
    # ... other middleware
]

XRAY_RECORDER = {
    'AWS_XRAY_TRACING_NAME': 'payments-api',
    'AUTO_INSTRUMENT': True,
    'AWS_XRAY_CONTEXT_MISSING': 'LOG_ERROR',
}
```

## Node.js (Express)

### Install

```bash
npm install aws-xray-sdk-core
```

### Express middleware

```javascript
const awsXRay = require('aws-xray-sdk-core');
const express = require('express');

const app = express();

// Apply middleware BEFORE all routes
app.use(awsXRay.express.openSegment('payments-api'));

// Patch AWS SDK for downstream tracing
const AWS = awsXRay.captureAWS(require('aws-sdk'));

// Patch HTTP/HTTPS for non-AWS downstream calls
awsXRay.captureHTTPsGlobal(require('https'));
awsXRay.captureHTTPsGlobal(require('http'));

// Routes
app.post('/checkout', async (req, res) => {
  const segment = awsXRay.getSegment();
  segment.addAnnotation('order_id', req.body.order_id);
  segment.addMetadata('payment_method', 'stripe');

  const dynamo = new AWS.DynamoDB();
  // This call is auto-traced as a subsegment
  await dynamo.putItem({...}).promise();
  res.json({ status: 'ok' });
});

// Close middleware AFTER all routes
app.use(awsXRay.express.closeSegment());
```

### Capture function calls

```javascript
const awsXRay = require('aws-xray-sdk-core');

const processPayment = awsXRay.captureAsyncFunc(
  'process_payment',
  async (segment, orderId) => {
    segment.addAnnotation('order_id', orderId);
    return chargeCard(orderId);
  }
);
```

## Java (Spring Boot)

### Install (Maven)

```xml
<dependency>
  <groupId>com.amazonaws</groupId>
  <artifactId>aws-xray-recorder-sdk-core</artifactId>
  <version>2.15.0</version>
</dependency>
<dependency>
  <groupId>com.amazonaws</groupId>
  <artifactId>aws-xray-recorder-sdk-aws-sdk-v2</artifactId>
  <version>2.15.0</version>
</dependency>
```

### Servlet filter (Spring Boot)

```java
import com.amazonaws.xray.javax.servlet.AWSXRayServletFilter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class XRayConfig {
    @Bean
    public FilterRegistrationBean<AWSXRayServletFilter> tracingFilter() {
        FilterRegistrationBean<AWSXRayServletFilter> registration = new FilterRegistrationBean<>(
            new AWSXRayServletFilter("payments-api")
        );
        registration.setOrder(1);
        return registration;
    }
}
```

### AWS SDK v2 instrumentation

```java
import com.amazonaws.xray.AWSXRay;
import com.amazonaws.xray.handlers.TracingHandler;
import software.amazon.awssdk.core.client.builder.SdkClientBuilder;

TracingHandler handler = new TracingHandler();
DynamoDbClient dynamo = DynamoDbClient.builder()
    .overrideConfiguration(o -> o.addExecutionInterceptor(handler))
    .build();
```

### Annotations and metadata

```java
import com.amazonaws.xray.AWSXRay;

AWSXRay.getCurrentSegment().putAnnotation("order_id", orderId);
AWSXRay.getCurrentSegment().putMetadata("payment_method", "stripe");
```

## Go

### Install

```bash
go get github.com/aws/aws-xray-sdk-go
```

### HTTP handler

```go
import (
    "net/http"
    "github.com/aws/aws-xray-sdk-go/xray"
)

func main() {
    http.Handle("/", xray.Handler(xray.NewFixedSegmentNamer("payments-api"), http.HandlerFunc(handler)))
    http.ListenAndServe(":8080", nil)
}

func handler(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context()
    xray.AddAnnotation(ctx, "order_id", "ord-12345")
    xray.AddMetadata(ctx, "payment_method", "stripe")
    // ... handler logic
}
```

### AWS SDK instrumentation

```go
import (
    "github.com/aws/aws-xray-sdk-go/awsdk"
    "github.com/aws/aws-sdk-go-v2/config"
)

cfg, _ := config.LoadDefaultConfig(context.TODO())
awsdk.AppendMiddleware(&cfg) // patches all AWS SDK v2 clients
```

## .NET (ASP.NET Core)

### Install

```bash
dotnet add package AWSXRayRecorder.Core
dotnet add package AWSXRayRecorder.Handlers.AspNetCore
dotnet add package AWSXRayRecorder.Handlers.AwsSdk
```

### Startup

```csharp
using Amazon.XRay.Recorder.Core;
using Amazon.XRay.Recorder.Handlers.AspNetCore;
using Amazon.XRay.Recorder.Handlers.AwsSdk;

public class Startup {
    public void ConfigureServices(IServiceCollection services) {
        AWSSDKHandler.RegisterXRayForAllServices();
        services.AddControllers();
    }

    public void Configure(IApplicationBuilder app) {
        app.UseXRay("payments-api");
        app.UseRouting();
        app.UseEndpoints(e => e.MapControllers());
    }
}
```

### Annotations and metadata

```csharp
using Amazon.XRay.Recorder.Core;

AWSXRayRecorder.Instance.AddAnnotation("order_id", orderId);
AWSXRayRecorder.Instance.AddMetadata("payment_method", "stripe");
```

## Lambda Powertools (Python — recommended for Lambda)

```python
from aws_lambda_powertools import Tracer

tracer = Tracer(service="payments-api")

@tracer.capture_lambda_handler
def handler(event, context):
    order_id = event["order_id"]
    tracer.put_annotation("order_id", order_id)
    result = process_payment(order_id)
    return {"status": "ok", "result": result}

@tracer.capture_method
def process_payment(order_id):
    # Auto-traced as a subsegment
    return charge_card(order_id)
```

Powertools auto-patches `boto3` for downstream AWS calls and propagates
the trace context from the Lambda runtime. No manual segment management
needed.

## Annotation vs metadata

| Feature | Annotations | Metadata |
|---|---|---|
| Indexable in X-Ray console | Yes | No |
| Searchable in trace queries | Yes | No |
| Value types | String, Number, Boolean | Any JSON-serializable |
| Use for | `customer_id`, `environment`, `region` | Request/response bodies, debug info |
| Cost impact | High-cardinality annotations bloat index | Minimal |
| Example | `put_annotation("customer_id", "cust-123")` | `put_metadata("request_body", {...})` |

**NEVER annotate with high-cardinality fields** (`request_id`, `timestamp`,
`trace_id`). The annotation index grows unbounded and degrades X-Ray query
performance. Use metadata for these.

## Trace context propagation

The X-Ray SDK propagates trace context via the `X-Amzn-Trace-Id` HTTP
header. For traces to span services, the header MUST be forwarded.

### HTTP (ALB / API Gateway)

ALB and API Gateway auto-inject the `X-Amzn-Trace-Id` header. The X-Ray
SDK middleware reads it and creates a child segment. No manual
propagation needed for synchronous HTTP calls.

### SQS

The SDK does NOT auto-propagate through SQS. The producer must set the
`AWSTraceHeader` system attribute:

```python
import json
from aws_xray_sdk.core import xray_recorder

segment = xray_recorder.current_segment()
trace_header = segment.get_origin_trace_header() if hasattr(segment, 'get_origin_trace_header') else None

# Or construct manually from the trace ID
sqs.send_message(
    QueueUrl=queue_url,
    MessageBody=json.dumps(payload),
    MessageSystemAttributes={
        'AWSTraceHeader': {
            'DataType': 'String',
            'StringValue': f"Root={segment.trace_id};Parent={segment.id};Sampled=1"
        }
    }
)
```

The consumer reads the header and starts a subsegment with the parent
trace ID. Lambda automatically reads `AWSTraceHeader` — no code needed
on the Lambda side.

### EventBridge

EventBridge does NOT propagate X-Ray trace context. Each Lambda invoked
by EventBridge starts a new trace. Use the `AWSTraceHeader` detail field
and manual propagation if cross-service tracing is needed.

### SNS

SNS propagates the `X-Amzn-Trace-Id` header to SQS subscriptions (not
to HTTP / Lambda subscriptions without configuration). Set
`AWSTraceHeader` as a message attribute.

## OpenTelemetry / ADOT migration

### Why migrate

The X-Ray SDK is in maintenance mode. AWS recommends ADOT (AWS Distro
for OpenTelemetry) for new deployments. ADOT supports:

- W3C `traceparent` header (vendor-neutral)
- Multiple backends (X-Ray, Jaeger, Datadog, etc.)
- The OTel Collector (replaces the X-Ray daemon)

### ADOT Collector for ECS (sidecar)

```json
{
  "name": "aws-otel-collector",
  "image": "public.ecr.aws/aws-observability/aws-otel-collector:v0.40.0",
  "essential": true,
  "cpu": 256, "memory": 512,
  "portMappings": [
    {"containerPort": 4317, "protocol": "tcp"}
  ],
  "environment": [
    {"name": "AWS_REGION", "value": "<region>"}
  ],
  "command": ["--config=/etc/otel-config/ecs-xray.yaml"],
  "logConfiguration": {
    "logDriver": "awslogs",
    "options": {
      "awslogs-group": "/ecs/aws-otel-collector",
      "awslogs-region": "<region>",
      "awslogs-stream-prefix": "otel"
    }
  }
}
```

The app sends traces to `127.0.0.1:4317` (gRPC OTLP format) instead of
`127.0.0.1:2000` (UDP X-Ray format).

### OTel SDK (Python example)

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

trace.set_tracer_provider(TracerProvider(
    resource=Resource.create({"service.name": "payments-api"})
))
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4317"))
))

# Auto-instrument Flask and botocore
FlaskInstrumentor().instrument_app(app)
BotocoreInstrumentor().instrument()
```

## Full NEVER list (14 items)

1. NEVER deploy the X-Ray SDK without `xray:GetSamplingRules` and
   `xray:GetSamplingTargets` on the app role. Central sampling rules are
   never applied without these.
2. NEVER run the daemon without `xray:PutTraceSegments` and
   `xray:PutTelemetryRecords`. Traces are silently dropped.
3. NEVER set `FixedRate=1.0` on the Default rule for high-traffic
   services. Massive cost.
4. NEVER forget to patch the AWS SDK. Downstream AWS calls won't appear
   in the service map.
5. NEVER deploy the daemon as a separate ECS service on Fargate and
   point the app to it via DNS. Use a sidecar.
6. NEVER annotate with high-cardinality fields (`request_id`,
   `timestamp`). Index bloat degrades query performance.
7. NEVER put secrets in annotations or metadata. Annotations and
   metadata are visible in the X-Ray console. Use `put_metadata` with a
   redacted value.
8. NEVER set `context_missing="RUNTIME_ERROR"`. This crashes the app if
   a segment is accessed outside a request context. Use `"LOG_ERROR"`.
9. NEVER forget trace context propagation for SQS / EventBridge. Each
   service starts a new trace without it, breaking the service map.
10. NEVER set EKS DaemonSet resource limits too low. The daemon can
    OOM-kill under high trace volume, silently dropping traces.
11. NEVER use the X-Ray daemon 3.x for new deployments. Use 4.x or ADOT
    Collector. 3.x is deprecated.
12. NEVER enable X-Ray on Lambda without Powertools for clean annotation
    syntax. Manual segment management is error-prone.
13. NEVER share one sampling rule across vastly different services
    without scoping via `ServiceName` or `Attributes`. A 100% rule for a
    critical endpoint floods other services.
14. NEVER forget the `AWS_XRAY_DAEMON_ADDRESS` env var on ECS EC2
    daemon-as-a-service. The app defaults to `127.0.0.1:2000` which is
    wrong when the daemon is on the host.

## Pre-flight safety CLI

```bash
# App role has all 5 X-Ray actions
aws iam get-role-policy --role-name <app-role> --policy-name <policy-name> \
  --query 'PolicyDocument.Statement[0].Action'

# Or check managed policy attachment
aws iam list-attached-role-policies --role-name <app-role> \
  --query 'AttachedPolicies[?contains(PolicyName, `XRay`)]'

# Daemon is running (ECS)
aws ecs describe-task-definition --task-definition <family> \
  --query 'taskDefinition.containerDefinitions[?contains(name, `xray`)]'

# Daemon is running (EKS)
kubectl get daemonset -n kube-system aws-xray-daemon

# Lambda tracing enabled
aws lambda get-function-configuration --function-name <name> \
  --query 'TracingConfig.Mode'

# Sampling rules configured
aws xray get-sampling-rules --query 'SamplingRuleRecords[*].SamplingRule.RuleName'

# VPC endpoint exists (if private VPC)
aws ec2 describe-vpc-endpoints \
  --filter Name=service-name,Values=com.amazonaws.<region>.xray \
  --query 'VpcEndpoints[*].VpcEndpointId'

# Encryption config
aws xray get-encryption-config --query 'EncryptionConfig.Type'
```

## Edge cases

- **Cross-account tracing:** use CloudWatch cross-account observability.
  The trace context propagates via `X-Amzn-Trace-Id`. ServiceLens
  aggregates the cross-account service map.
- **SQS trace propagation:** the producer sets `AWSTraceHeader` system
  attribute. Lambda auto-reads it. Non-Lambda consumers must read it
  manually and start a subsegment.
- **EKS IRSA vs instance profile:** if using IRSA (IAM Roles for Service
  Accounts), the DaemonSet ServiceAccount must have the X-Ray role
  annotation. The app pods do NOT need the role — the daemon uploads
  traces, not the app.
- **High-trace-volume cost control:** set the Default rule to 1% for
  high-traffic services. Use custom rules scoped to critical endpoints.
  Monitor trace count via CloudWatch metric `XRayTracesPublished`.
- **OTel migration coexistence:** the X-Ray SDK and OTel SDK can run
  side by side during migration. The X-Ray backend accepts both X-Ray
  format (from the daemon) and OTLP format (from the ADOT Collector).
  Migrate one service at a time.
- **Daemon UDP buffer overflow:** under high trace volume, the daemon's
  UDP buffer (default 2 MB) can overflow. Increase the buffer with the
  daemon flag `-b <bytes>`. Symptoms: dropped traces, no error log.
