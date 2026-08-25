# EC2 Spot Interruption - Advanced Patterns

Expert behaviors and recent features - moved verbatim from SKILL.md.

### Step 0: Expert knowledge — non-obvious EC2 Spot interruption behaviors

These behaviors are easy to misjudge without operational Spot
experience. Each changes a plan if ignored:

- **The 2-minute warning is a maximum, not a guarantee.** Design the
  graceful-shutdown pipeline to complete within 90 seconds. Some
  interruption scenarios (capacity-reclaim) may provide less notice.
  EventBridge is the ONLY notification channel — there is no SNS,
  email, or CloudWatch Alarm for Spot interruptions.

- **`InstanceInterruptionBehavior` is set at launch and immutable.**
  Options: `terminate` (default), `stop` (EBS-backed), `hibernate`
  (requires `--hibernate-options Configured=true`). If the Spot
  request is cancelled, stopped/hibernated instances cannot restart
  as Spot — they become On-Demand or remain stopped.

- **Capacity rebalance is proactive, not reactive.** ASG
  `CapacityRebalance` monitors Spot placement risk and launches
  replacements BEFORE the 2-minute warning. Enable for production
  ASGs to reduce actual interruptions experienced.

- **`capacity-optimized` over `lowest-price` for production.**
  `lowest-price` selects the cheapest pool (highest interruption rate).
  `capacity-optimized` selects pools with the lowest interruption rate
  at a 5-10% cost premium for 10-100x better availability.

- **Diversification math: 3 families x 3 AZs = 9 pools.** Interruption
  rates are roughly independent across pools. With 9 pools, the
  probability of all being interrupted simultaneously is negligible —
  the basis for the 99.9% availability claim. Mix Intel, AMD, and
  Graviton (`c5`, `m5`, `c6g`) across 3+ AZs.

- **Spot placement score is a forecast, not a guarantee.**
  `get-spot-placement-scores` estimates fulfillment likelihood (10 =
  highly recommended; 1 = unlikely). Run BEFORE launching large fleets.
  The score is a snapshot — it does not guarantee future availability.

- **Spot Block is deprecated (2024+).** No new requests accepted. Use
  On-Demand Capacity Reservations for predictable capacity.

- **ELB deregistration delay must fit within 2 minutes.** The ALB
  default of 300 seconds means the instance is terminated before
  draining finishes. Set to 30-60 seconds for Spot targets.

- **ASG lifecycle hooks fire on termination, not on the warning.**
  The `InstanceTerminating` hook places the instance in
  `Terminating:Wait` — but the Spot interruption terminates after 2
  minutes regardless. The lifecycle hook does NOT extend the window.

- **Spot Fleet auto-replaces interrupted instances.** No manual
  intervention needed for capacity restoration — but replacements
  start from scratch (no state migration). Stateful workloads must
  checkpoint independently.

- **Graviton (arm64) Spot often has lower interruption rates.** Newer
  pools with more spare capacity. Include in diversification for both
  cost and resilience. Verify application supports arm64.

- **`describe-spot-instance-requests` `StatusCode` for early warning.**
  `marked-for-stop` or `marked-for-termination` indicates imminent
  interruption. `fulfilled` means healthy.

## Recent AWS features (2024-2026)

- **Capacity Rebalance GA:** ASG `CapacityRebalance` proactively
  monitors Spot risk and launches replacements BEFORE the 2-minute
  warning. Enable for production ASGs.

- **Spot Placement Score API:** `get-spot-placement-scores` forecasts
  fulfillment likelihood. Score 10 = "highly recommended"; 1 = "very
  unlikely." Run before launching large fleets.

- **`capacity-optimized-prioritized`:** Honors `Priority` in Overrides
  when pools have equal capacity. Use when you have preferred types.

- **Spot Block deprecation (2024+):** No new requests accepted. Use
  On-Demand Capacity Reservations for predictable capacity.

- **Graviton4 Spot (c7g, m7g, r7g):** Newer pools with lower
  interruption rates. Include in diversification for cost + resilience.

- **MixedInstancesPolicy SpotPercentage:** Control the Spot vs On-Demand
  ratio. 50-70% Spot balances savings with On-Demand baseline.

- **IMDSv2 required (2024):** All new EC2 launches (including Spot)
  must enforce `HttpTokens: required`. Verify launch templates.
