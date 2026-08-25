# EC2 Spot Interruption - Error Handling

Failure-mode table and malformed-input protocol moved verbatim from SKILL.md.

**Interruption-handling failure-mode table:**

| Symptom | Root cause | Fix |
|---|---|---|
| EventBridge rule fired but Lambda never invoked | Lambda reserved concurrency = 0, OR resource-based policy missing `events.amazonaws.com` | `put-function-concurrency --reserved-concurrent-executions 5`; add `lambda:InvokeFunction` permission for `events.amazonaws.com` |
| Lambda invoked but timed out | Lambda timeout too short (< 60s), OR S3/DynamoDB write is slow | `update-function-configuration --timeout 90`; check checkpoint target latency |
| Lambda completed but instance not deregistered from ELB | Lambda lacks `elasticloadbalancing:DeregisterTargets`, OR wrong target group ARN | Add the permission; verify the target group ARN in the Lambda env |
| Instance deregistered but ELB still sending traffic | `deregistration_delay.timeout_seconds` > 120 (longer than the 2-minute window) | Modify the target group: `modify-target-group-attributes --attributes Key=deregistration_delay.timeout_seconds,Value=30` |
| Spot Fleet did not auto-replace | `TargetCapacity` dropped, OR `ExcessCapacityTerminationPolicy` misconfigured, OR all pools exhausted | Verify `TargetCapacity`; check `describe-spot-fleet-request-history` for launch failures |
| ASG did not launch replacement | `DesiredCapacity` already met by On-Demand, OR `MixedInstancesPolicy` spot percentage = 0 | Verify `SpotAllocationStrategy` and `SpotPercentage`; check ASG activity |
| Repeated interruptions on the same instance type | Single pool, high interruption rate in that AZ | Diversify: add more instance types and AZs; switch to `capacity-optimized` |
| Stateful work lost despite pipeline | Checkpoint not written before termination (pipeline too slow) | Reduce checkpoint latency; use async writes; consider `InstanceInterruptionBehavior: stop` |

## Malformed input

**Malformed input:** if the input JSON is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: Spot/Fleet/ASG configuration
is not valid JSON or is missing required fields — cannot plan.` and
`REMEDIATION: Re-fetch with aws ec2 describe-spot-instance-requests
--spot-instance-request-id <id> --output json and re-plan.`
