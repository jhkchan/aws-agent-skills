# Eval prompt: vpc-peering-not-enabled-blocked

Design a deployment plan for a Lightsail instance that needs to reach
a private RDS database. Emit the standard VERDICT block.

Requirements:

- Instance name: prod-app
- Blueprint: ubuntu_22_04 (OS-only)
- Bundle: small_3_0 (2 GB RAM, 2 CPU)
- AZ: us-east-1a
- Static IP: required (prod-app-ip allocated)
- DNS: zone app.example.com; A record app → static IP
- VPC peering: required — the instance must reach RDS at
  db-private.xxxxxxx.us-east-1.rds.amazonaws.com (private IP,
  in the default EC2-VPC)

Existing-account context: `aws lightsail is-vpc-peered --region us-east-1`
returns `false`. The RDS instance has `publicly-accessible: false`
and its security group allows inbound from the Lightsail VPC CIDR
(`172.26.0.0/16`) — but VPC peering has never been enabled in this
region. The team expects the Lightsail instance to reach RDS by
private IP immediately on launch.
