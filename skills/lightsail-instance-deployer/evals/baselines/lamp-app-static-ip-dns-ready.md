# Baseline (no-skill) response: lamp-app-static-ip-dns-ready

This file captures what a generic assistant produces WITHOUT the
lightsail-instance-deployer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, enumerated CHECKLIST,
specific DEPLOY_COMMANDS, blueprint/bundle validation, static IP
ordering gate, snapshot addon configuration, firewall CIDR scoping).

---

Here's a plan to set up your LAMP instance on Lightsail.

The instance will:

- Run LAMP 8 on a medium bundle
- Have a static IP
- DNS pointing to it
- Daily snapshots
- Firewall on 22, 80, 443

Steps:

1. Create the instance with the LAMP blueprint.
2. Attach the static IP.
3. Set up the DNS A record.
4. Enable automatic snapshots.
5. Configure the firewall.

Commands:

```
aws lightsail create-instances --instance-names prod-lamp \
  --blueprint-id lamp_8 --bundle-id medium_3_0 ...
aws lightsail attach-static-ip ...
aws lightsail create-domain-entry ...
```

This should give you a working LAMP server. Let me know if you need
help with any of the steps.
