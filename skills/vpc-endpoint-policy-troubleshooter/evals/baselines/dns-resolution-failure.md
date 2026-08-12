# Baseline (no-skill) — dns-resolution-failure

> This is the response a model produces **without** the skill
> definition. It suggests generic DNS troubleshooting (check
> resolv.conf, VPC DNS settings) but misses the specific root cause:
> private DNS is disabled on the interface endpoint, causing the EC2
> service DNS name to resolve to a public IP instead of the endpoint
> ENI. It does not mention the private DNS flag or how to enable it.
> Generated for with-skill-vs-baseline comparison.

---

Check the VPC DNS settings. Make sure enableDnsHostnames and
enableDnsSupport are enabled. Also check the Route 53 resolver
settings.

```bash
aws ec2 describe-vpc-attribute --vpc-id vpc-xxx --attribute enableDnsHostnames
dig ec2.us-east-1.amazonaws.com
```

If the DNS resolves to a public IP, you may need to configure
custom DNS routing or use the endpoint DNS name directly.
