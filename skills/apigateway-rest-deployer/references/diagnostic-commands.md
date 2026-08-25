# Diagnostic commands - API Gateway REST Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Pre-flight: deployment specification gate — live-account pre-flight checks
**Live-account pre-flight checks (skip if doing offline architecture plan):**
1. Verify IAM permissions for `apigateway:CreateRestApi`, `CreateResource`,
   `PutMethod`, `PutIntegration`, `CreateAuthorizer`, `CreateUsagePlan`,
   `CreateApiKey`, `CreateDeployment`, `CreateStage`, `UpdateStage`,
   `apigatewayv2:CreateApi`, `CreateDomainName`, `CreateVpcLink`, and
   `wafv2:CreateWebACL`, `wafv2:AssociateWebACL`.
2. For Lambda integrations, verify the function exists in the same region
   and the API Gateway service has `lambda:InvokeFunction` permission.
3. For VPC Link, verify the NLB exists and has target groups in multiple
   AZs.
4. For Cognito authorizers, verify the user pool exists and the app client
   is configured.
5. For custom domains, verify the ACM certificate is ISSUED in the same
   region as the API (REGIONAL) or us-east-1 (EDGE).


## Verification commands (run after deployment)

```bash
# Verify API is deployed and stage exists
aws apigateway get-stage --rest-api-id <id> --stage-name prod

# Verify all methods have correct authorization
aws apigateway get-methods --rest-api-id <id> \
  --query 'items[*].[httpMethod,authorizationType,authorizerId]'

# Verify usage plan and keys are linked
aws apigateway get-usage-plans --query 'items[?apiStages[?apiId==`<id>`]]'
aws apigateway get-usage-plan-keys --usage-plan-id <plan-id>

# Verify WAF is associated
aws apigatewayv2 get-web-acl-for-resource --resource-arn arn:aws:apigateway:<region>::/restapis/<id>/stages/prod

# Verify access logging is configured
aws apigateway get-stage --rest-api-id <id> --stage-name prod \
  --query 'accessLogSettings'

# Test invocation (with valid auth)
curl -X GET https://<api-id>.execute-api.<region>.amazonaws.com/prod/users \
  -H "Authorization: Bearer <jwt>"

# Verify custom domain mapping
aws apigateway get-base-path-mappings --domain-name api.example.com
```


