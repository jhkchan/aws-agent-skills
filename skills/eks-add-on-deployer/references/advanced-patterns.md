# Advanced Patterns (load on demand) — EKS Add-On Deployer

Expert-knowledge deep dives, edge cases, appendices, and recent AWS feature notes moved verbatim from SKILL.md. Loaded on demand.

---

## Expert heuristic: EKS-managed vs self-managed conflict lifecycle (moved from SKILL.md)

The most common EKS add-on failure is a conflict between the EKS-managed
add-on and a pre-existing self-managed installation. A baseline model
may say "just create the add-on"; the conflict resolution strategy
determines whether your customizations survive.

```text
Scenario: cluster already has self-managed vpc-cni (aws-node DaemonSet)

create-addon --addon-name vpc-cni
  --resolve-conflicts OVERWRITE  → EKS replaces self-managed config (YOUR CUSTOMIZATIONS LOST)
  --resolve-conflicts RETAIN     → EKS keeps self-managed config (your customizations survive, but EKS may not fully manage)
  --resolve-conflicts NONE       → CONFLICT reported, add-on status = DEGRADED

update-addon --addon-name vpc-cni
  --resolve-conflicts OVERWRITE  → EKS overwrites on every update (not recommended for customized add-ons)
  --resolve-conflicts PRESERVE   → preserves existing fields, applies new defaults for unset fields
```

**Key implication:** if you have customized a self-managed add-on (e.g.,
custom env vars on `aws-node`), use `RETAIN` on first create and
`PRESERVE` on updates. `OVERWRITE` silently destroys your customizations.
The safe pattern is: export current config, create the EKS add-on with
`RETAIN`, then migrate customizations to `--configuration-values`.

**Operational pattern for migration from self-managed to EKS-managed:**
1. Export the current self-managed add-on config (e.g., `kubectl get
   ds aws-node -n kube-system -o yaml`).
2. Create the EKS add-on with `--resolve-conflicts OVERWRITE` to take
   control.
3. Re-apply customizations via `--configuration-values` using the EKS
   add-on API (not kubectl).
4. Verify the add-on status is `ACTIVE`.


## IRSA vs Pod Identity comparison (Step 4) (moved from SKILL.md)

**IRSA vs Pod Identity comparison:**

| Feature | IRSA | EKS Pod Identity |
|---|---|---|
| Credential delivery | OIDC federation + projected token | Pod Identity Agent + ephemeral credentials |
| Setup complexity | OIDC provider + trust policy per SA | Agent add-on + IAM association |
| OIDC provider required | Yes | No |
| Multi-account support | Complex trust policies | Simpler cross-account |
| Migration status | Mature, widely supported | Newer (2024+), growing support |


## Migration from IRSA to Pod Identity (Step 5) (moved from SKILL.md)

**Migration from IRSA to Pod Identity:**
1. Install `eks-pod-identity-agent`.
2. Create a new IAM role with Pod Identity trust policy.
3. Create Pod Identity association for the service account.
4. Remove the old IRSA role annotation from the service account.
5. Verify pods pick up the new credentials (pod restart required).


## Recent features (Step 8) (moved from SKILL.md)

- **EKS Pod Identity (2024):** New credential delivery method using
  the `eks-pod-identity-agent` add-on. Simpler than IRSA — no OIDC
  provider required. Uses `pods.eks.amazonaws.com` trust principal.
- **EKS Auto Mode (2024-2025):** Automatically manages vpc-cni,
  kube-proxy, coredns, and node lifecycle. Manual add-on management is
  not needed for these on Auto Mode clusters.
- **EKS Hybrid Nodes (2024-2025):** On-premises nodes join EKS clusters.
  Add-ons require hybrid-specific configurations for non-VPC networking.
- **Add-on configuration values schema validation (2024-2025):** EKS
  now validates `--configuration-values` JSON against the add-on's
  schema. Invalid keys are reported at creation/update time.
- **GuardDuty Agent EKS add-on (2024-2025):** Runtime threat detection
  as a managed EKS add-on. Requires Pod Identity or IRSA for the
  GuardDuty security account.
- **ADOT Operator add-on (2024-2025):** AWS Distro for OpenTelemetry
  as a managed EKS add-on with Operator pattern for automated
  collector deployment.
