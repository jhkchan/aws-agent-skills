# Eval prompt: 502-vpclink-unhealthy-target

Diagnose the 5xx failure for the following API Gateway stage. Walk the
error-code-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: clients of API jkl012 (stage prod) receive 502 BadGateway on
all requests to /internal-api. The integration is a VPC Link to an NLB
in a private VPC. The application behind the NLB was undergoing a
deployment when the 502s started.

API id: jkl012 (REST API, v1)
Stage: prod
Integration: VPC_LINK (connectionId: vpcl-aaa111) on GET /internal-api
aws apigateway get-vpc-links: vpcl-aaa111 state is AVAILABLE.
NLB target group tg-internal (behind vpcl-aaa111):
  aws elbv2 describe-target-health returns:
    - Target: i-backend-1, State: unhealthy,
      Reason: Target.FailedHealthChecks,
      Description: "Health checks failed"
    - Target: i-backend-2, State: unhealthy,
      Reason: Target.FailedHealthChecks,
      Description: "Health checks failed"
Target group health check: HTTP GET /health on port 8080, interval 30s,
  timeout 5s, healthy threshold 3, unhealthy threshold 3.
No Lambda function is configured for this API.
Access log integrationStatus: 502 with integrationErrorMessage:
  "Execution failed due to a backend error."
CloudTrail: no Lambda Invoke events for this API in the failure window.
API Gateway Count metric: stable (requests are arriving).
API Gateway 5XXError metric: spikes matching Count.

Emit the standard diagnostic block (TARGET, VERDICT, REASON, LAYER,
EVIDENCE, REMEDIATION).
