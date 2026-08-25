# EC2 Spot Fleet Deployer — error handling (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).
## Error handling (moved from SKILL.md)

### Fleet stuck in `submitted`/`active` with 0 instances
- No capacity in the specified pools. Check Spot placement score;
  diversify by adding instance types/AZs. Switch to
  `capacityOptimized` if using `lowestPrice`. Verify the IAM service
  role (`AWSServiceRoleForEC2SpotFleet`) exists.

### Fleet partially filled (e.g., 10 of 20 target)
- Add more instance types (m5a, c5, r5 families) and AZs. Consider
  switching to `priceCapacityOptimized` if using `lowestPrice`.

### Capacity rebalance not working
- Verify fleet type is `maintain` (not `request`). Verify
  `ReplacementStrategy` is `launch`. Check EventBridge for rebalance
  recommendation events.

### `MaxSpotInstanceCountExceeded`
- Account hit the Spot vCPU limit. Request a quota increase via
  Service Quotas. Use vCPU-based quotas (now default).

### Allocation strategy cannot be changed
- Immutable after creation. Cancel the fleet
  (`cancel-spot-fleet-requests`) and create a new one.
