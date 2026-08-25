# Diagnostic commands - API Gateway HTTP API Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Live-account pre-flight checks

**Live-account pre-flight checks (skip if doing offline plan):**
1. Verify IAM permissions for `apigatewayv2:CreateApi`, `CreateRoute`,
   `CreateIntegration`, `CreateAuthorizer`, `CreateStage`,
   `UpdateStage`, `CreateDomainName`, `CreateApiMapping`,
   `UpdateRoute`, and `wafv2:CreateWebACL`, `wafv2:AssociateWebACL`.
2. For Lambda integrations, verify the function exists in the same
   region and grant `lambda:InvokeFunction` to the
   `apigateway.amazonaws.com` principal scoped to the API's source ARN.
3. For VPC link, verify the NLB exists and target groups span multiple
   AZs. **NLB only — ALB is not a valid target.**
4. For JWT authorizers, verify the OIDC issuer returns a valid OpenID
   configuration with a JWKS URI, and that the audience claim matches
   an issued `client_id`.
5. For custom domains, verify the ACM certificate is `ISSUED` in the
   API's region (`REGIONAL` only — HTTP API does not support EDGE).

## Step 7: access logging (JSON)

```bash
aws apigatewayv2 update-stage --api-id <id> --stage-name '$default' \
  --access-log-settings DestinationArn=arn:aws:logs:<region>:<account>:log-group:prod-http-api-access,Format='{"requestId":"$context.requestId","ip":"$context.identity.sourceIp","requestTime":"$context.requestTime","httpMethod":"$context.httpMethod","routeKey":"$context.routeKey","status":"$context.status","responseLength":"$context.responseLength","latency":$context.integrationLatency,"errorMessage":"$context.error.message"}'
```

CloudWatch Logs Insights query:
```
fields @timestamp, status, latency, ip
| filter status >= 400
| stats count() by status
```

## Verification commands (run after deployment)

```bash
aws apigatewayv2 get-api --api-id <id>
aws apigatewayv2 get-routes --api-id <id> --query 'Items[*].[RouteKey,AuthorizationType,Target]'
aws apigatewayv2 get-integrations --api-id <id> --query 'Items[*].[IntegrationType,IntegrationMethod,IntegrationUri]'
aws apigatewayv2 get-authorizer --api-id <id> --authorizer-id <auth-id>
aws apigatewayv2 get-api --api-id <id> --query 'CorsConfiguration'
aws apigatewayv2 get-stage --api-id <id> --stage-name '$default'
aws apigatewayv2 get-web-acl-for-resource --resource-arn arn:aws:apigateway:<region>::/apis/<id>/stages/$default
aws apigatewayv2 get-api-mappings --domain-name api.example.com

# Live invocation
curl -X GET https://<api-id>.execute-api.<region>.amazonaws.com/health
curl -X GET https://<api-id>.execute-api.<region>.amazonaws.com/users -H "Authorization: Bearer <jwt>"
```
