# Baseline (no-skill) — gateway-endpoint-missing-route

> This is the response a model produces **without** the skill
> definition. It suggests checking the endpoint status and IAM
> policies but misses the specific root cause: the Gateway endpoint
> is not in route table rtb-private-2, causing S3 traffic from
> subnet-private-2 to go via the NAT Gateway. It does not mention
> the route table layer at all. Generated for with-skill-vs-baseline
> comparison.

---

Check that the endpoint is available and the endpoint policy is
correct. The NAT Gateway usage might be expected behavior or a
routing issue.

```bash
aws ec2 describe-vpc-endpoints --vpc-endpoint-ids vpce-s3gw456
```

Verify the IAM policies allow S3 access. If traffic still goes
through NAT, you might need to recreate the endpoint.
