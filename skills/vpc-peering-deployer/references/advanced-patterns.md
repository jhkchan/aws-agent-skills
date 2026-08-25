# Advanced Patterns — VPC Peering Deployer

Deep reference content moved verbatim from `vpc-peering-deployer/SKILL.md`. Loaded on demand;
see SKILL.md for the condensed core and its quick navigation.

## Step 10 — recent AWS features (2023-2026)

**Recent AWS features (2023-2026):**

- **IPv6 VPC peering maturity (2023-2024):** Full IPv6 support for VPC
  peering connections, including inter-region IPv6 peering. Both VPCs
  must have IPv6 CIDR blocks assigned.

- **Inter-region VPC peering performance (2023-2024):** AWS backbone
  optimization for inter-region peering traffic, reducing latency and
  improving throughput for cross-region workloads. Inter-region peering
  uses the AWS global backbone (not the public internet).

- **CloudWatch VPC peering metrics (2023-2024):** Enhanced metrics for
  peering connection traffic monitoring, including bytes/data transfer
  per peering connection.

- **Peering connection tags (2023-2024):** VPC peering connections now
  support tagging for cost allocation and governance.

- **Terraform provider improvements (2023-2024):** The Terraform
  `aws_vpc_peering_connection` and `aws_vpc_peering_connection_accepter`
  resources now support inter-region peering with proper provider
  aliasing and auto-accept options for same-account.

- **Inter-region data transfer cost optimization (2024-2025):** AWS
  reduced inter-region data transfer pricing for peering connections in
  select region pairs, making inter-region peering more cost-effective
  for cross-region replication and DR.
