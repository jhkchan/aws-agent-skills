# Baseline (no-skill) response: vpc-peering-not-enabled-blocked

This file captures what a generic assistant produces WITHOUT the
lightsail-instance-deployer skill loaded — the contrast that proves
the skill catches the missing VPC peering blocker that the baseline
misses (Lightsail's VPC is isolated from EC2-VPC; peering is
required for private RDS access).

---

Here's a plan to set up your Lightsail instance with RDS access.

The instance will:

- Run Ubuntu 22.04 on a small bundle
- Have a static IP
- DNS pointing to it
- Reach the RDS database at db-private.xxxxxxx.us-east-1.rds.amazonaws.com

Steps:

1. Create the instance.
2. Attach the static IP.
3. Configure the DNS A record.
4. Install your application and connect to RDS.

Commands:

```
aws lightsail create-instances --instance-names prod-app \
  --blueprint-id ubuntu_22_04 --bundle-id small_3_0 ...
aws lightsail attach-static-ip ...
```

Your application should be able to reach RDS via the private endpoint.
Let me know if you have trouble connecting.
