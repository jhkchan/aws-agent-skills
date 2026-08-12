# Eval: response-stream-none

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — RESPONSE_STREAM + NONE auth, public streaming endpoint, CORS allow all origins, handler uses awslambda.streamifyResponse

## Prompt

Create a Lambda function URL for function
my-streaming-handler (runtime nodejs20.x) in us-east-1.
Use NONE auth and RESPONSE_STREAM invoke mode for public
LLM token streaming. CORS should allow all origins, methods
GET and POST, header content-type, max age 3600. The handler
uses awslambda.streamifyResponse. Function timeout 15s.
Tags: Environment=production, Service=streaming-api.
