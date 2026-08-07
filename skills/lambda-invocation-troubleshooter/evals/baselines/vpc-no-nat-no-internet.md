# Baseline (no-skill) response: vpc-no-nat-no-internet

---

Your Lambda function can't reach api.stripe.com. Since the function
was recently VPC-attached, that's probably related. Check that the
security group allows outbound HTTPS traffic — port 443 should be
open to 0.0.0.0/0.

If the security group is fine, you might need a VPC endpoint or a NAT
gateway. Lambda functions in a VPC don't automatically get internet
access.
