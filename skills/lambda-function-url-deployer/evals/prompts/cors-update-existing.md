# Eval: cors-update-existing

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — update-function-url-config with expanded CORS (add staging origin, PUT/DELETE methods, x-api-key header), preserves existing auth and invoke mode

## Prompt

Update the function URL for my-api-handler in us-east-1.
Current CORS allows https://app.example.com. Add
https://staging.example.com as an allowed origin. Add PUT
and DELETE to allowed methods. Add x-api-key to allowed
headers. Set max age to 3600. The URL uses AWS_IAM auth
and BUFFERED invoke mode.
