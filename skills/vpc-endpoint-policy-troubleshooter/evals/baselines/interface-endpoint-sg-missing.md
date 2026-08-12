# Baseline (no-skill) — interface-endpoint-sg-missing

> This is the response a model produces **without** the skill
> definition. It suggests generic VPC troubleshooting steps but
> misses the specific root cause: the endpoint's own security group
> (sg-vpce123) does not allow inbound on port 443 from the client
> subnet 10.0.2.0/24. It checks the client security group, route
> tables, and VPC settings but does not identify that the endpoint
> ENI's SG is the blocker. Generated for with-skill-vs-baseline
> comparison.

---

The endpoint seems to be created correctly. Check the client
security group to make sure it allows outbound on port 443. Also
verify the VPC route tables are correct. You can try restarting
the EC2 instances or recreating the endpoint.

```bash
aws ec2 describe-vpc-endpoints --vpc-endpoint-ids vpce-aaa111222
```
