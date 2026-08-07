# Eval: missing-cmk-and-key-schema

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — partition key design and CMK ARN both unspecified

## Prompt

Help me create a new DynamoDB table called "orders-prod" in us-east-1.
It needs SSE-KMS encryption. We will store order data — I think
orderId should be the key but not sure about distribution. Region:
us-east-1, Account: 123456789012.
