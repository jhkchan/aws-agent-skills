# Baseline (no-skill) response: vpc-link-private-integration

This file captures what a generic assistant produces WITHOUT the
apigateway-rest-deployer skill loaded — the contrast that proves the
skill adds structure (VPC Link requires NLB not ALB, HTTP_PROXY
integration with connectionType VPC_LINK, IAM auth for service-to-
service, security group source rules for VPC Link ENIs).

---

To expose your private ECS service via API Gateway, you can use a VPC
Link to your load balancer.

Architecture:

- REST API in us-east-1
- Resources: /orders, /orders/{id}
- Integration: HTTP via VPC Link to NLB
- IAM auth
- Custom domain: internal-api.example.com

Steps:

1. Create the VPC Link targeting your NLB.
2. Create the REST API.
3. Configure HTTP integration using the VPC Link.
4. Set IAM auth on the methods.
5. Deploy.

The VPC Link will let API Gateway reach your private NLB without going
over the internet. Make sure your NLB is configured for TCP 443.

You'll need to add a WAF and access logging for production.

Commands:

```
aws apigateway create-vpc-link --target-arns <nlb-arn>
aws apigateway create-rest-api ...
aws apigateway put-integration --type HTTP --connection-type VPC_LINK
```

Let me know if you need help with the security group configuration.
