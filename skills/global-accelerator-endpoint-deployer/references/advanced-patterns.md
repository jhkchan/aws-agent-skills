# Advanced Patterns — Global Accelerator Endpoint Deployer

Edge-case catalogs and recent AWS features moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Step 10 — Recent features (moved from SKILL.md)

- **Dual-stack anycast IPs (2023-2024):** IPv6 anycast alongside IPv4.
  Use `--ip-address-type DUAL_STACK` at creation.
- **Cross-account endpoint support (2023-2024):** Endpoints can reference
  resources in different AWS accounts within an organization.
- **Endpoint weight granular control (2023-2024):** Zero-weight draining
  for individual endpoints without removal.
- **Custom routing accelerators (2023-2024):** Port-based routing to
  specific endpoints for non-HTTP protocols.
- **BYOIP IPv6 support (2024-2025):** BYOIP now supports IPv6 CIDRs for
  dual-stack accelerators.
- **Flow logs enhancements (2024-2025):** Endpoint health transitions
  and traffic dial changes captured in flow logs.
- **Health check protocol expansion (2024-2025):** Additional protocols
  including gRPC health probes.

