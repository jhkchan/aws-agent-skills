# Advanced Patterns — VPC Lattice Service Deployer

Deep reference content moved verbatim from `vpclattice-service-deployer/SKILL.md`. Loaded on demand;
see SKILL.md for the condensed core and its quick navigation.

## Step 13 — recent features (2023-2026)

- **VPC Lattice GA (2023):** Service networks, services, target groups,
  listener rules, and IAM auth policies.
- **gRPC support (2023-2024):** Full gRPC protocol for services,
  including gRPC health checks and gRPC-specific listener rules.
- **Lambda TG event structure 2.0 (2023-2024):** Lambda target groups
  use an improved event structure with Lattice metadata.
- **Cross-account via RAM (2023-2024):** RAM resource shares enable
  cross-account VPC association with a shared service network.
- **Custom domain with ACM TLS (2023-2024):** ACM-managed TLS certs
  (us-east-1) for user-facing custom domain names.
- **Access log subscription (2024-2025):** Structured access log
  delivery to CloudWatch Logs or S3.
- **Weighted traffic splitting (2024-2025):** Listener rules support
  weighted forwarding to multiple target groups for canary/blue-green.
- **Header-based routing (2024-2025):** Listener rules support header
  matching in addition to path-based and method-based routing.
- **Tiered pricing (2025-2026):** Reduced per-GB cost above monthly
  thresholds for high-volume workloads.
