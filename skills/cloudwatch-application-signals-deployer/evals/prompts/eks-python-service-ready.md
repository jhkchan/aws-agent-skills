# Eval: eks-python-service-ready

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — EKS Python via Operator inject webhook, dual SLO

## Prompt

Enable CloudWatch Application Signals on the search-api service
running on EKS in us-east-1. Runtime: Python 3.11. The
OpenTelemetry Operator is installed; the deployment is
annotated instrumentation.opentelemetry.io/inject-python="true".
The service account has IAM roles via IRSA with
CloudWatchApplicationSignalsReportServiceAccess and
AWSXrayWriteOnlyAccess attached. X-Ray sampling FixedRate=0.10.
Service discovery via Kubernetes services. Create a 99.9%
availability SLO plus a p95 latency SLO (250ms target).
Account: 123456789012.
