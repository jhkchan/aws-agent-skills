# Diagnostic Commands (load on demand) — EKS Add-On Deployer

Pre-flight, diagnostic, and verification command listings moved verbatim from SKILL.md. Loaded on demand.

---

## Add-on enumeration commands (Step 1) (moved from SKILL.md)

**List available add-ons for a cluster:**

```bash
aws eks describe-addon-versions \
  --kubernetes-version 1.30 \
  --query 'addons[*].addonName' --output table
```

**Check which add-ons are already installed:**

```bash
aws eks list-addons --name my-cluster --output table
```


## Version compatibility check command (Step 2) (moved from SKILL.md)

**Check add-on version compatibility:**

```bash
aws eks describe-addon-versions \
  --addon-name vpc-cni \
  --kubernetes-version 1.30 \
  --query 'addons[0].addonVersions[*].{Version:addonVersion,Default:compatibilities[0].defaultVersion}' \
  --output table
```


## Auto Mode check command (Step 6) (moved from SKILL.md)

**Check if a cluster uses Auto Mode:**

```bash
aws eks describe-cluster --name my-cluster --query 'cluster.computeConfig'
```
