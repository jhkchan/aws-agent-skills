# Error handling — lambda-function-url-deployer

> Content moved verbatim from SKILL.md during progressive-disclosure
> restructuring. Load on demand.

## Error handling

### Browser preflight (OPTIONS) fails with CORS error
- The function URL does not have CORS configured. Add the `--cors`
  parameter to the function URL config with AllowOrigins,
  AllowMethods, and AllowHeaders. CORS is at the function URL level,
  not the Lambda function level.

### Function URL returns 403 Forbidden
- If auth type is AWS_IAM, the caller's request is not properly
  signed with SigV4, or the resource-based policy does not grant
  `lambda:InvokeFunctionUrl` to the caller. Verify the policy with
  `aws lambda get-policy`.

### Function URL returns 504 Timeout
- The handler exceeded the 15-second function URL invocation cap.
  Reduce handler execution time, use RESPONSE_STREAM mode to start
  streaming earlier, or move long-running work to async invocation.

### RESPONSE_STREAM returns a runtime error
- The handler signature does not match RESPONSE_STREAM expectations.
  Ensure the handler uses `awslambda.streamifyResponse` (Node.js) or
  the equivalent streaming wrapper for the runtime. Verify the
  runtime supports streaming.

### Function URL points to wrong alias
- The function URL is still on `$LATEST`. Update with
  `--qualifier <alias>` to point at the intended alias.

### CloudFront returns 502/503
- The origin (function URL) is unreachable or returning errors.
  Verify the function URL works directly first. Check CloudFront
  origin settings — the origin must be the full function URL
  hostname.

