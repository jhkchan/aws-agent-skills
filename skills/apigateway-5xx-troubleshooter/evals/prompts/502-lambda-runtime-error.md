# Eval prompt: 502-lambda-runtime-error

Diagnose the 5xx failure for the following API Gateway stage. Walk the
error-code-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: clients of API mno345 (stage prod) receive 502 BadGateway on
GET /users/{id} after the most recent deployment. The Lambda function
was updated to read a TABLE_NAME environment variable that was not set
in the function configuration. The function crashes before returning a
proxy response.

API id: mno345 (REST API, v1)
Stage: prod
Integration: AWS_PROXY (Lambda proxy) on GET /users/{id}
Lambda function: users-handler
Lambda CloudWatch logs (matching request timestamps):
  "ERROR: ReferenceError: process.env.TABLE_NAME is undefined"
  "Runtime.LogError: ..." with full stack trace.
  "Task timed out" is NOT present in any log entry.
Lambda Invocations metric: spikes matching 5xxError spikes.
Lambda Errors metric: spikes matching 5xxError (Errors = Invocations).
Lambda Duration metric: 15-30ms (function crashes immediately).
Lambda Throttles metric: zero.
Access log integrationErrorMessage: "Malformed Lambda proxy response"
  (Lambda returned no proxy response because it crashed).
Access log integrationLatency: 20-35ms.
aws lambda invoke with a test payload returns:
  FunctionError: "Unhandled"
  Payload: {"errorMessage": "process.env.TABLE_NAME is not defined",
            "errorType": "ReferenceError",
            "stackTrace": [...]}

Emit the standard diagnostic block (TARGET, VERDICT, REASON, LAYER,
EVIDENCE, REMEDIATION).
