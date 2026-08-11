# Eval: lambda-java-slo

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — Lambda Java via ADOT layer

## Prompt

Enable CloudWatch Application Signals on the auth-api Lambda
function in us-east-1. Runtime: Java 21 (arm64). The
aws-otel-java-wrapper-arm64 layer is attached. The function
execution role has both required managed policies. X-Ray
sampling FixedRate=0.05 (Lambda respects the Default rule).
AWS_SERVICE_NAME=auth-api, AWS_APPLICATION_ENVIRONMENT=prod.
Create a 99.9% availability SLO over 28 days rolling with
burn-rate alarms (fast 5m/14.4x, medium 1h/6x, slow 6h/3x).
Account: 123456789012.
