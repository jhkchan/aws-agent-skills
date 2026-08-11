# Eval prompt: wait-invalidation-completed

Verify the following CloudFront invalidation has reached Completed
status and emit the standard VERDICT block (post-verification form:
OPERATION, VERDICT, TARGET, PRE_CHECKS, POST_VERIFY, COST, NOTES).

Operation: wait-invalidation
DistributionId: E1ABC2DEF3GHI4
InvalidationId: I2XYZ5678UVW90

```json
{
  "Invalidation": {
    "Id": "I2XYZ5678UVW90",
    "Status": "Completed",
    "CreateTime": "2026-08-10T15:30:00Z",
    "InvalidationBatch": {
      "CallerReference": "inv-20260810-001",
      "Paths": {
        "Quantity": 1,
        "Items": ["/*"]
      }
    }
  },
  "SpotCheck": {
    "Url": "https://d111111abcdef8.cloudfront.net/index.html",
    "HttpStatus": "200 OK",
    "XCache": "Miss from CloudFront",
    "Age": 0
  }
}
```
