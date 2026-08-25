# Worked Examples (load on demand) — CloudWatch Application Signals Deployer

Secondary worked examples and configuration payloads moved verbatim from SKILL.md. Loaded on demand.

---

## Step 3: language-specific auto-instrumentation injection examples (moved from SKILL.md)

**Java (ECS Fargate — sidecar pattern):**

Add the ADOT collector sidecar AND inject the auto-instrumentation Java
agent into the application container:

```yaml
# ECS task definition excerpt
containerDefinitions:
  - name: payments-api
    image: <image>
    environment:
      - name: AWS_SERVICE_NAME
        value: payments-api
      - name: AWS_APPLICATION_ENVIRONMENT
        value: prod
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: http://localhost:4317
      - name: OTEL_RESOURCE_ATTRIBUTES
        value: service.name=payments-api,service.namespace=payments
      - name: JAVA_TOOL_OPTIONS
        value: -javaagent:/opt/aws-opentelemetry-agent/aws-opentelemetry-agent.jar
    dependsOn:
      - containerName: aws-otel-collector
        condition: START

  - name: aws-otel-collector
    image: public.ecr.aws/aws-observability/aws-otel-collector:latest
    command: ["--config=/etc/otel-collector-config.yaml"]
    # config ships traces to X-Ray and metrics to CloudWatch Application Signals
```

**Java (EKS — mutating webhook):**

Install the ADOT operator and the OpenTelemetry Agent Injector. The
injector mutates pods that have the annotation
`instrumentation.opentelemetry.io/inject-java: "true"`:

```bash
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm install opentelemetry-operator open-telemetry/opentelemetry-operator \
  --namespace opentelemetry-operator-system --create-namespace

# Annotate the workload
kubectl annotate deploy payments-api \
  instrumentation.opentelemetry.io/inject-java="true" \
  instrumentation.opentelemetry.io/otel-exporter-otlp-endpoint="http://localhost:4317"
```

**Python (ECS / EKS — same pattern):**

```bash
# Python auto-instrumentation is via the opentelemetry-instrument package
# Inject via the OTel Operator with:
kubectl annotate deploy payments-api \
  instrumentation.opentelemetry.io/inject-python="true"
```
---

## Step 8: Availability and Latency SLO examples (CloudFormation) (moved from SKILL.md)

**Availability SLO (CloudFormation):**

```yaml
Type: AWS::ApplicationSignals::ServiceLevelObjective
Properties:
  Name: payments-api-availability-slo
  Description: 99.9% successful requests over 28 days rolling
  EvaluationType: PeriodBased
  Goal:
    Interval:
      RollingInterval:
        DurationUnit: DAY
        Duration: 28
      BurnRates:
        - RollupInterval: MINUTE
        - RollupInterval: HOUR
    AttainmentGoal: 0.999
    WarningThreshold: 0.995
  RequestBasedSliConfig:
    MetricThreshold: 200  # HTTP 2xx/3xx/4xx are success, 5xx is fault
    GoodRequestsMetric:
      MetricStat:
        Metric:
          Namespace: AWS/ApplicationSignals
          MetricName: CallCount
          Dimensions:
            - Name: ServiceName
              Value: payments-api
            - Name: Environment
              Value: prod
        Period: 60
        Stat: Sum
```

**Latency SLO (target percentile):**

```yaml
RequestBasedSliConfig:
  MetricThreshold: 0.25  # seconds — p95 must be under 250ms
  TotalRequestsMetric:
    MetricStat:
      Metric:
        Namespace: AWS/ApplicationSignals
        MetricName: Latency
        ...
      Stat: "p95"
```
