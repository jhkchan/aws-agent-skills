# Baseline (no-skill) — insufficient-data-endpoint

> This is the response a model produces **without** the skill
> definition. It guesses at common causes (security groups, route
> tables, endpoint state) without identifying the specific evidence
> gaps that prevent diagnosis. It does not structure the missing data
> or explain why each missing piece is critical for isolating the
> failure layer. Generated for with-skill-vs-baseline comparison.

---

Try checking the endpoint state and security groups. The issue
could be a security group, routing, or the endpoint service.

```bash
aws ec2 describe-vpc-endpoints --vpc-endpoint-ids vpce-unknown999
```

If the endpoint looks fine, check the client security group and
network ACLs. You may also want to recreate the endpoint.
