# Baseline (no-skill) response: vpc-link-private-integration

This file captures what a generic assistant produces WITHOUT the
apigateway-http-api-deployer skill loaded. The contrast proves the
skill adds the VPC link contract (NLB-only target, subnet + security
group creation order, HTTP_PROXY with connection-id, AWS_IAM sigv4
per-route).

---

Here's a plan for your HTTP API with private backend integration.

Architecture:

- HTTP API in us-east-1
- Routes: GET /internal/health, GET /internal/orders,
  POST /internal/orders
- Backend: NLB `prod-internal-nlb` via VPC link
- AWS_IAM authorization

Steps:

1. Create the HTTP API.
2. Add routes.
3. Set up VPC link to your NLB.
4. Configure HTTP_PROXY integration.
5. Set up IAM auth.

Commands:

```
aws apigatewayv2 create-api ...
aws apigatewayv2 create-vpc-link ...
aws apigatewayv2 create-integration ...
```

Make sure your NLB is reachable from the VPC link subnets.
