# Eval prompt: wordpress-bundle-lb-ha-ready

Design a deployment plan for a production HA Lightsail WordPress
deployment. Emit the standard VERDICT block.

Requirements:

- Two instances: prod-wp-1 (AZ us-east-1a), prod-wp-2 (AZ us-east-1b)
- Blueprint: wordpress (app+OS)
- Bundle: medium_3_0 (4 GB RAM, 2 CPU, 80 GB SSD, 4 TB transfer) —
  meets the WordPress minimum
- Load balancer: Lightsail LB prod-wp-lb on port 443 with TLS,
  sticky sessions (duration-based, 1 hour), health check path /,
  interval 10 sec
- Snapshots: automatic daily at 03:00 UTC, 7-day retention, plus a
  manual snapshot before each update
- Firewall: 443 from 0.0.0.0/0 (LB → instance); 22 from corporate
  CIDR 10.0.0.0/8
- VPC peering: not required

Existing-account context: the team is migrating from a single
WordPress instance that was overloaded during traffic spikes. The
two new instances will share traffic via the Lightsail LB with sticky
sessions (WordPress stores sessions in files by default). WordPress
media assets are stored on each instance's local disk; a shared
storage solution is out of scope for this deploy.
