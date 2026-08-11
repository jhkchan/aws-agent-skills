# Baseline (no-skill) response: wordpress-bundle-lb-ha-ready

This file captures what a generic assistant produces WITHOUT the
lightsail-instance-deployer skill loaded — the contrast that proves
the skill adds structure (HA pattern validation, Lightsail LB Layer 4
constraint surfacing, sticky session requirement for file-based
sessions, multi-AZ AZ selection, deterministic VERDICT block).

---

Here's a plan to set up HA WordPress on Lightsail.

The deployment will:

- Two WordPress instances in different AZs
- A Lightsail load balancer in front
- Daily snapshots
- Firewall on 443 and 22

Steps:

1. Create two instances with the WordPress blueprint.
2. Create a Lightsail load balancer.
3. Attach both instances to the load balancer.
4. Enable TLS on the load balancer.
5. Enable daily snapshots on both instances.

Commands:

```
aws lightsail create-instances --instance-names prod-wp-1 prod-wp-2 \
  --blueprint-id wordpress --bundle-id medium_3_0 ...
aws lightsail create-load-balancer ...
aws lightsail attach-instances-to-load-balancer ...
```

This should give you HA WordPress. Note that you may want sticky
sessions on the load balancer. Let me know if you need help.
