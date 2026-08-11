# Eval: basic-alias-versioned

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — alias points to published version 5, API Gateway stage uses alias qualifier, CloudWatch alarm scoped to alias

## Prompt

Create a Lambda alias named prod for function my-function
pointing to published version 5. Set up API Gateway
integration so API abc123 stage prod invokes the alias.
Create a CloudWatch alarm for errors scoped to the alias.
Region us-east-1. Tags: Environment=production, Service=api.
Account: 123456789012.
