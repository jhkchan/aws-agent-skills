# Baseline (no-skill) response: missing-acm-domain-cert

This file captures what a generic assistant produces WITHOUT the
apigateway-rest-deployer skill loaded — the contrast that proves the
skill adds structure (detection of missing ACM cert as a hard blocker
for custom domain mapping, explicit PREREQUISITES_MISSING verdict,
refusal to silently fall back to the default execute-api endpoint).

---

Here's a plan for your health check REST API.

Architecture:

- REST API in us-east-1
- Resources: /health
- Lambda proxy: health-check-handler
- Public endpoint (no auth)
- Custom domain: api.example.com

Steps:

1. Create the REST API.
2. Add /health resource with GET method.
3. Configure Lambda proxy integration.
4. Set up the custom domain api.example.com.
5. Deploy.

You'll need to provide an ACM certificate at some point for the custom
domain. For now, the API will work via the default
`*.execute-api.us-east-1.amazonaws.com` endpoint until you add the cert.

The health check endpoint should return 200 OK for your load balancer.

Let me know once you have the ACM cert and I'll help you set up the
custom domain mapping.
