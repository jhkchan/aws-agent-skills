# NAT Gateway Cost Optimizer — Advanced Patterns and Recent Features

Recent AWS features moved verbatim from SKILL.md. Load on demand.

## Recent AWS features (2024-2026)

- **Gateway Load Balancer endpoints (expanded 2024-2025):** For security
  appliance insertion (firewalls, IDS/IPS). Not a cost-optimisation lever,
  but relevant to VPC endpoint topology. Surface as a finding if the VPC
  uses third-party security appliances.

- **VPC endpoint policies for S3 (enhanced 2024):** Support for
  condition-key-based policies (e.g., restricting to specific IAM roles).
  Use for least-privilege Gateway endpoint configurations.

- **CloudWatch Network Monitor (2024-2025):** Proactive monitoring of
  network paths including NAT Gateway. Use to establish a baseline before
  optimisation and to verify no latency regression post-change.

- **Cost Explorer NAT Gateway granularity (2024):** Cost Explorer now
  separates NAT Gateway base (hourly) from data-processing (per-GB) in the
  usage-type dimension. Use this split to quantify the base-cost vs
  data-processing contribution.

- **Graviton-based NAT Instances (2024-2025):** t4g.micro NAT AMIs offer
  better price-performance than t3.micro for NAT Instance workloads.
  Consider t4g for new NAT Instance deployments.
