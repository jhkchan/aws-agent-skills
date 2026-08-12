# Baseline (no-skill) response: explicit-deny-bucket-policy

---

Your Lambda function can't write to the bucket. The execution role has
s3:PutObject permission, so that should be fine. Check the bucket
policy for any Deny statements.

There seems to be a Deny based on source IP. Since the Lambda function
is behind a NAT Gateway, its IP might not match the corporate CIDR.
You could try adding the NAT Gateway IP to the allowed list, or remove
the Deny statement.
