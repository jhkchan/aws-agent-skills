# Baseline (no-skill) response: instance-not-registered-agent-stopped

---

Your instance `i-0abcdef1234567890` is not showing up in SSM. This
is usually because the instance role is missing permissions or the
instance doesn't have internet access. Check that the
AmazonSSMManagedInstanceCore policy is attached and that the
security group allows outbound 443.

If that looks right, you might need to reinstall the SSM Agent on
the instance or reboot it to re-register.
