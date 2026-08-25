# Error Handling (load on demand) — EC2 Launch Template Deployer

Launch-template and RunInstances failure modes — architecture mismatch at boot, InvalidParameterCombination from cross-VPC security groups, IMDSv2 silently unenforced, capacity-reservation not consumed, and orphaned EBS volumes — moved verbatim from SKILL.md.


---

## Error handling — launch/RunInstances failure modes (moved from SKILL.md)

**Instance fails to boot (pending → shutting-down):** architecture
mismatch (x86_64 AMI on Graviton) — verify `describe-images`
Architecture matches instance family. User data syntax error —
validate with `base64 --decode` before encoding.

**`InvalidParameterCombination` at RunInstances:** security group
from a different VPC than the subnet — verify all SGs share the
subnet's VpcId. `SecurityGroupIds` (top-level) AND
`NetworkInterfaces.Groups` both set — use only the latter for VPC.

**IMDSv2 not enforced despite template setting:** `HttpEndpoint=
disabled` overrides `HttpTokens=required`. Hop limit too low for
containerized workloads — set to 2 or 3 for ECS/EKS/Docker.

**Capacity reservation not consumed:** `targeted` ODCR with wrong
`InstanceType`, `AvailabilityZone`, or `InstancePlatform` — verify
fields match exactly. Reservation may be `cancelled`/`expired`.

**EBS volume not deleted on termination:** `DeleteOnTermination=
false` on non-root volume (the default) — set explicitly to `true`.
