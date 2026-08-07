# Baseline (no-skill) response: missing-required-fields

This file captures what a generic assistant produces WITHOUT the
apigateway-rest-deployer skill loaded — the contrast that proves the
skill adds structure (PREREQUISITES_MISSING verdict with enumerated
REQUIRED fields, refusal to silently pick defaults for API type and
integration type).

---

Here's a plan for your API Gateway API.

Architecture:

- API in us-east-1
- Resource: /items [GET]
- IAM auth
- REGIONAL endpoint

Steps:

1. Create the API.
2. Add /items resource with GET method.
3. Configure IAM auth.
4. Deploy.

I'll use sensible defaults for the rest — REST API v1 (the standard
type), Lambda proxy integration, standard throttling. You can swap in
the right integration later when you know what backend you want.

Commands:

```
aws apigateway create-rest-api --name items-api
aws apigateway create-resource ...
aws apigateway put-method --authorization-type AWS_IAM
aws apigateway put-integration --type AWS_PROXY
aws apigateway create-deployment
```

Let me know what backend you want to integrate with and I can refine.
