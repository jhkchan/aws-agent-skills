# Baseline (no-skill) response: vpc-endpoint-ssmmessages-missing

---

Your session is timing out even though the instance shows Online.
Since the instance is in a private subnet, you likely need a VPC
endpoint for SSM. Try adding a VPC endpoint for the SSM service and
make sure the security group allows outbound 443.

If the endpoint is already there, check that private DNS is enabled
and that the instance role has the `ssmmessages` permissions.
