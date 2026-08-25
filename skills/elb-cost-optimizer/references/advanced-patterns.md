# ELB Cost Optimizer — advanced patterns (load on demand)

Expert-knowledge deep dives and recent features, moved verbatim from SKILL.md.

## Expert heuristic — LCU is max not sum, consolidate to cut the floor, idle is free money (moved verbatim from SKILL.md lines 522-549)


Three rules, in order, produce 90% of ELB savings:

1. **LCU dimension maximization.** ALB bills on the MAX of four
   dimensions, not the sum. Identify the peak dimension and focus all
   optimization there. If new connections is the peak at 20 LCU, then
   reducing active connections from 5 LCU to 0 saves nothing. Enable
   keep-alive (reduces new connections by 80%+), compress responses
   (reduces processed bytes), and simplify rules (reduces rule
   evaluations). The peak dimension determines the bill.

2. **Multi-path routing to consolidate ALBs.** Each ALB costs
   $16.43/month minimum. Ten ALBs cost $164/month. Consolidating to
   three ALBs (one per environment: prod, staging, dev) using host-based
   and path-based routing saves $114/month. Use a single multi-domain
   TLS certificate (SAN) to cover all hostnames.

3. **CLB elimination urgency.** Every CLB is $18.25/month plus per-GB
   charges, with no path routing, no LCU-based pricing, and no new
   features. Migrating CLBs to ALBs is both a cost saving ($1.82/month
   per CLB on hourly rate alone) and a feature upgrade. Prioritize CLBs
   with the highest traffic — the per-GB savings are larger.

**The idle LB is the lowest-hanging fruit.** A single idle ALB at
$16.43/month costs $197/year for nothing. In accounts with 10+
ALBs, typically 2-3 are idle (leftover from testing, deprecated
services, or blue/green standby). Deleting them is 100% savings with
zero risk.

## Recent AWS features (2024-2026) (moved verbatim from SKILL.md lines 588-606)


- **ALB Zonal DNS Exclusion (2024-2025):** ALB now supports zonal DNS
  exclusion, allowing you to route traffic only to specific AZs. This
  reduces cross-AZ data transfer for workloads with geographically
  concentrated clients.
- **NLB cross-zone traffic visibility (2024-2025):** CloudWatch now
  provides per-AZ metrics for NLB cross-zone traffic, making it easier
  to quantify the cost impact of cross-zone load balancing.
- **ALB access log partitioning (2025-2026):** ALB access logs now
  support S3 partitioning by date and load balancer name, improving
  query performance and reducing Athena scan costs for log analysis.
- **L7 load balancer capacity unit improvements (2024-2026):** AWS
  has increased the LCU efficiency for ALBs handling HTTP/2 and HTTP/3
  (QUIC) traffic, reducing the effective LCU consumption for modern
  protocol workloads.
- **PrivateLink integration with ALB (2024-2026):** AWS PrivateLink
  now supports ALB as a resource, allowing private connectivity to ALB
  endpoints across VPCs without internet gateway or NAT gateway
  charges.
