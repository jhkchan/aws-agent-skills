# Advanced Patterns (load on demand) — EC2 Launch Template Deployer

Mindset, the configuration dependency graph, the IMDSv2 / Graviton / block-device expert heuristics, Step 10 CPU options and license specifications, and 2023-2026 feature notes, moved verbatim from SKILL.md.


---

## Mindset — three launch-template misconceptions (moved from SKILL.md)

**One-line takeaway:** A Launch Template is a versioned, parameter-
ized instance configuration that every EC2 provisioning surface
(RunInstances, Fleet, Auto Scaling Group, Spot Fleet, EKS managed
nodes, ECS) reads from. Getting the template right means every
downstream launch inherits correct security defaults; getting it
wrong propagates a misconfiguration to every instance in the fleet.

Three misconceptions dominate launch-template misdesign at
provisioning time:

- **"IMDSv2 is on by default."** It is not. New launch templates
  default to `HttpTokens=optional` unless you explicitly set
  `HttpEndpoint=enabled, HttpTokens=required`. Every baseline
  template without the IMDSv2 block leaves the instance vulnerable
  to SSRF-driven credential theft — the most common EC2 Security
  Hub finding.

- **"Any AMI works with any instance type."** Architecture must
  match. An x86_64 AMI on a Graviton (arm64) instance fails at boot
  with no console output clue. Always validate `Image.Architecture`
  against the instance family before creating the template version.

- **"Block device mapping is optional; AWS picks sensible defaults."**
  The default is `gp2` with the AMI snapshot size. Production
  workloads should explicitly set `gp3` (cheaper, tunable IOPS/
  throughput) and `DeleteOnTermination=true` to avoid orphaned-volume
  cost accumulation.

## Configuration dependency graph (novel heuristic) (moved from SKILL.md)

Launch-template settings are NOT independent. Many silently no-op
without their prerequisite; others are immutable per version. Use
this graph to sequence provisioning and debug "why is my instance
launching with the wrong config?" later.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| AMI | AMI exists in the region + Architecture matches instance type | **AMI architecture mismatch fails at BOOT, not at template creation** — template creates successfully, instance fails to boot | OS + baseline |
| Instance type | valid type + available in the AZ | burstable types accumulate CPU credits silently; Graviton requires arm64 AMI | compute shape |
| Key pair | key exists in the region | invalid key name fails at RunInstances, NOT at template creation | SSH access |
| Security groups | SGs exist in the VPC where the subnet lives | **SG from another VPC silently accepted in the template, fails at launch** | network ACL |
| IAM instance profile | profile exists and has a role attached | profile name without role attached → instance launches with no credentials | application IAM |
| User data | must be base64-encoded (CLI does this with `--user-data file://`) | **plain-text user data > 16 KB silently rejected by some provisioning surfaces**; use compressed or S3-sourced for large scripts | bootstrap |
| Block device (EBS) | valid volume type for the instance type | **instance store volumes (`VirtualName=ephemeralN`) silently ignored on instance types that have no instance store** | storage |
| Network interface | subnet + SG in the same VPC | **`AssociatePublicIpAddress` only honored on `DeviceIndex=0`** | network path |
| IMDSv2 (`HttpTokens=required`) | `HttpEndpoint=enabled` | hop limit defaults to 1; containers making IMDS calls need a higher hop limit | metadata security |
| Tag specifications | valid resource type (`instance`, `volume`, `network-interface`, `spot-instances-request`) | **tags on `spot-instances-request` apply only to the Spot request, not the instance** — set both | cost allocation |
| Capacity reservation targeting | reservation exists and is `open` or matches instance type + AZ + platform | **`targeted` reservation with no matching pool silently falls back to On-Demand** | guaranteed capacity |
| CPU options | valid core count / threads-per-core for the instance type | unsupported values fail at launch, not at template creation | licensing / perf |

**The architecture-mismatch and SG-cross-VPC rows are the ones a
baseline model misses.** Both create a template that looks valid
but fails at instance launch with a confusing error. The procedure
below forces an explicit architecture and VPC-consistency check
before the `create-launch-template` call.

**Cross-dependency gotchas:**
- A Graviton instance type (`c7g.large`, `m7g.large`) REQUIRES an
  arm64 AMI. x86_64 AMIs boot-loop or fail silently.
- `CapacityReservationSpecification.TargetCapacityReservationIds`
  is only valid when the reservation's `InstanceType`, `AvailabilityZone`,
  and `InstancePlatform` match the template's instance.
- `TagSpecifications` on `spot-instances-request` resource type only
  tags the Spot request; to tag the resulting instance, also include
  `instance` in the same list.
- IMDSv2 `HttpTokens=required` requires `HttpEndpoint=enabled`. If
  the endpoint is disabled, the `required` setting is silently
  ignored.

## Expert heuristic: IMDSv2 enforcement (moved from SKILL.md)

IMDSv2 (Instance Metadata Service v2) requires session-oriented,
token-based access to instance metadata. The older IMDSv1 allowed
simple GET requests, which SSRF attacks could exploit to steal
instance credentials. A baseline model mentions "enable IMDSv2"
without explaining the three interacting fields.

```text
HttpEndpoint:    enabled  (IMDS endpoint reachable)
HttpTokens:      required (v1 requests REJECTED — this is the IMDSv2 setting)
HttpPutResponseHopLimit: 1 (default) or higher for containers
```

**The single field that enforces IMDSv2 is `HttpTokens=required`.**
Setting `HttpEndpoint=enabled` alone leaves IMDSv1 available. The
three fields must be set together; the procedure forces all three.

**Hop limit gotcha:** containers (Docker, ECS task networking,
EKS pods) making IMDS calls traverse network hops. The default hop
limit of 1 blocks containerized IMDSv2 calls. Set `2` or `3` for
container workloads or the application silently fails to retrieve
credentials with no obvious error.

```json
{
  "MetadataOptions": {
    "HttpEndpoint": "enabled",
    "HttpTokens": "required",
    "HttpPutResponseHopLimit": 2,
    "InstanceMetadataTags": "enabled"
  }
}
```

**Key implication:** `HttpTokens=required` is the IMDSv2 enforcement
field. `HttpEndpoint=enabled` makes the endpoint reachable. Both
must be set together; hop limit must be tuned for containerized
workloads.

## Expert heuristic: Graviton (arm64) instance type selection (moved from SKILL.md)

Graviton (arm64) instances (c6g/c7g, m6g/m7g, r6g/r7g, t4g) offer
20-40% price-performance improvement over equivalent x86_64. The
catch: the AMI architecture must be `arm64`. A baseline model
suggests "switch to Graviton" without checking AMI compatibility.

```text
x86_64 → c5, c6i, c7i, m5, m6i, m7i, r5, r6i, r7i, t3
arm64  → c6g, c7g, m6g, m7g, r6g, r7g, t4g (Graviton)
```

**Verify before creating the template:**
```bash
aws ec2 describe-images --image-ids <ami-id> \
  --query 'Images[0].Architecture' --output text
# Must return "arm64" for Graviton, "x86_64" for Intel/AMD
```

**Key implication:** always verify `Image.Architecture` matches the
target family. An x86_64 AMI on a Graviton instance creates a valid
template but fails at boot — `pending → shutting-down` with no
obvious cause in the console output.

## Step 10 — CPU options and license specifications (moved from SKILL.md)

**CPU options** pin vCPU topology (useful for licensing):

```json
{
  "CpuOptions": { "CoreCount": 2, "ThreadsPerCore": 2 }
}
```

`CoreCount x ThreadsPerCore = total vCPUs`. Set `ThreadsPerCore: 1`
to disable hyperthreading for latency-sensitive or licensing-bound
workloads. Some instance types support `ThreadsPerCore` but not
arbitrary `CoreCount` — verify with `describe-instance-types`.

**License specifications** (BYOL for Windows / SQL Server):

```json
{
  "LicenseSpecifications": [{
    "LicenseConfigurationArn": "arn:aws:license-manager:us-east-1:123456789012:license-configuration:lic-0abc123"
  }]
}
```

## Step 11 — Recent features (2023-2026) (moved from SKILL.md)

**Recent AWS features (2023-2026):**

- **IMDSv2 as default for new launch templates (2024-2026 push):**
  AWS Security Hub finding `EC2.8` flags instances with IMDSv1
  available. New launch templates should set
  `HttpTokens=required` explicitly. The console defaults to
  `optional`; the CLI does not default at all.

- **Graviton4 (r8g, c8g, m8g, x8g — 2024-2025):** Fourth-generation
  Graviton with higher memory bandwidth and larger instance sizes
  (up to `x8g.16xlarge`). All Graviton families require arm64 AMIs.

- **gp3 default for new EBS volumes (2023-2024 push):** `gp3` is the
  recommended volume type for all production workloads. 20% cheaper
  than `gp2`, independent IOPS/throughput tuning. Default in the
  console is still `gp2`; always set explicitly in the template.

- **Instance Metadata Tags (2023-2024):** `InstanceMetadataTags:
  enabled` allows instances to retrieve their own tags via IMDSv2.
  Useful for self-identifying workloads.

- **Capacity Reservation Fleet targeting (2024-2025):** A Capacity
  Reservation Fleet can be targeted by ID, allowing the instance to
  consume capacity from any reservation in the fleet that matches.

- **Launch Template versioning with `$Default` and `$Latest`
  aliases:** RunInstances, ASG, and Fleet accept `$Latest` or
  `$Default` as the version. Pinning to a numeric version prevents
  silent drift; `$Latest` applies new versions automatically.
