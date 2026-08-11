# Baseline (no-skill) response: vpclink-nlb-config-incomplete

---

Your VPC link integration is returning 502. This means the request
reached the VPC link but the backend (NLB) couldn't process it.
Check that your NLB is running and that the target group has healthy
targets. Also verify the security groups are configured correctly
to allow traffic from the VPC link to the NLB.

You should also make sure the VPC link is in the same VPC as the NLB
and that the integration URI is correct.
