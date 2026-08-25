# Block Device and Network Interface Deep Dive — EC2 Launch Template Deployer

Detailed reference for block device mapping (EBS gp3 tuning, instance
store) and network interface configuration (subnet, public IP, IPv6,
security group placement). Loaded on-demand when the operator needs
to reason about storage topology or network configuration.

## EBS volume type comparison

| Type | IOPS | Throughput | Price vs gp2 | Use case |
|---|---|---|---|---|
| `gp3` | 3,000 (tunable 16,000) | 125 MB/s (tunable 1,000) | ~20% cheaper | **Default for production** |
| `gp2` | Sized (3 IOPS/GB, burst) | Tied to IOPS | Baseline | Legacy |
| `io2` / `io2 Block Express | Up to 256,000 | Up to 4,000 MB/s | Premium | Databases, sub-ms latency |
| `io1` | Up to 64,000 | Up to 1,000 MB/s | Premium | Legacy databases |
| `st1` | n/a | Up to 500 MB/s | Cheapest | Sequential (data lakes, logs) |
| `sc1` | n/a | Up to 250 MB/s | Lowest | Cold archives |

## gp3 IOPS and throughput tuning

`gp3` decouples IOPS and throughput from volume size, unlike `gp2`
which scales IOPS with capacity (3 IOPS/GB).

**Tuning limits:**
| Parameter | Baseline | Maximum | Increment |
|---|---|---|---|
| IOPS | 3,000 | 16,000 | 1 |
| Throughput (MB/s) | 125 | 1,000 | 1 |
| Volume size (GB) | 1 | 16,384 | 1 |

**Ratio constraint:** Throughput cannot exceed IOPS / 4. To sustain
1,000 MB/s throughput, you need at least 4,000 IOPS. A baseline
3,000 IOPS caps throughput at ~750 MB/s even if you request 1,000.

**Cost optimization:** Only provision IOPS/throughput above baseline
when the workload requires it. A web server on 3,000 IOPS / 125 MB/s
costs ~20% less than the same on gp2; tuning to 16,000 IOPS costs
~4x the baseline gp3 price.

```json
{
  "Ebs": {
    "VolumeSize": 100,
    "VolumeType": "gp3",
    "Iops": 6000,
    "Throughput": 250,
    "DeleteOnTermination": true,
    "Encrypted": true
  }
}
```

## Instance store volumes

Instance store disks are physically attached to the host. They are
ephemeral — data is lost on stop/start, hibernate, or instance
retirement.

**Eligible instance types:** `m5d`, `m5dn`, `c5d`, `c5dn`, `r5d`,
`r5dn`, `i3`, `i3en`, `i4i`, `x2ied`, `mac1.metal`, `p4d`, `p5`,
`g5`, `inf1`, `dl1`. The `d` suffix denotes instance store NVMe.

**Block device mapping:**
```json
{
  "BlockDeviceMappings": [
    { "DeviceName": "/dev/sdb", "VirtualName": "ephemeral0" },
    { "DeviceName": "/dev/sdc", "VirtualName": "ephemeral1" }
  ]
}
```

**Silent failure:** `VirtualName=ephemeralN` on an instance type
without physical disks is silently ignored — the mapping entry is
present but no device is attached. There is no error signal.

**Verification after launch:**
```bash
aws ec2 describe-instances --instance-ids <id> \
  --query 'Reservations[0].Instances[0].BlockDeviceMappings'
lsblk  # on the instance itself
```

## DeleteOnTermination defaults

| Volume source | Default `DeleteOnTermination` |
|---|---|
| Root volume (from AMI snapshot) | `true` |
| Non-root EBS added via block device mapping | `false` |
| EBS attached after launch (AttachVolume) | `false` |

**Implication:** non-root volumes added in the launch template
default to NOT being deleted on termination. For stateless / ephemeral
workloads, explicitly set `DeleteOnTermination=true` to avoid
orphaned-volume cost accumulation.

## Network interface (ENI) configuration

The `NetworkInterfaces` array in a launch template defines the
primary ENI (`DeviceIndex=0`) and optionally secondary ENIs.

### Key fields

| Field | Purpose | Notes |
|---|---|---|
| `DeviceIndex` | Interface index | `0` is primary; `AssociatePublicIpAddress` only honored here |
| `SubnetId` | Subnet for the ENI | VPC must match all SGs |
| `Groups` | Security group IDs | Use inside `NetworkInterfaces`, NOT top-level `SecurityGroupIds` |
| `AssociatePublicIpAddress` | Assign a public IPv4 | Only on `DeviceIndex=0` |
| `Ipv6AddressCount` | Number of IPv6 addresses | Subnet must have IPv6 CIDR |
| `PrivateIpAddresses` | Specific private IPs | Primary + secondary |
| `NetworkCardIndex` | For enhanced networking | Multiple cards (e.g., `c5n.18xlarge`) |
| `InterfaceType` | `interface` or `efa` | EFA for HPC / ML |

### SecurityGroupIds vs NetworkInterfaces.Groups

```json
// CORRECT: use Groups inside NetworkInterfaces for VPC instances
{
  "NetworkInterfaces": [{
    "DeviceIndex": 0,
    "SubnetId": "subnet-0abc123",
    "Groups": ["sg-0abc", "sg-0def"]
  }]
}

// AVOID: top-level SecurityGroupIds is silently overridden if
// NetworkInterfaces is also present
{
  "SecurityGroupIds": ["sg-0abc"],       // SILENTLY IGNORED
  "NetworkInterfaces": [{
    "DeviceIndex": 0,
    "Groups": ["sg-0def"]                // This wins
  }]
}
```

**Rule:** if `NetworkInterfaces` is present, its `Groups` field is
authoritative. Do not also set top-level `SecurityGroupIds`.

### IPv6 configuration

```json
{
  "NetworkInterfaces": [{
    "DeviceIndex": 0,
    "SubnetId": "subnet-0abc123",
    "Ipv6AddressCount": 1
  }]
}
```

**Prerequisites:**
- The VPC must have an assigned IPv6 CIDR block.
- The subnet must have an IPv6 CIDR block.
- The route table must have an IPv6 route (e.g., `::/0` → internet
  gateway for dual-stack, or egress-only gateway for IPv6 egress).

### Enhanced networking and EFA

For high-performance workloads (HPC, ML training), use `InterfaceType:
"efa"` (Elastic Fabric Adapter) for low-latency node-to-node
communication:

```json
{
  "NetworkInterfaces": [{
    "DeviceIndex": 0,
    "InterfaceType": "efa",
    "Groups": ["sg-0abc"],
    "SubnetId": "subnet-0abc123"
  }]
}
```

**Eligible types:** `c5n.18xlarge`, `c5n.9xlarge`, `g4dn`, `p4d`,
`p5`, `inf1`, `dl1`, `trn1`.

### Multiple network cards

High-throughput instances (`c5n.18xlarge`, `p4d.24xlarge`) support
multiple network cards:

```json
{
  "NetworkInterfaces": [
    { "DeviceIndex": 0, "NetworkCardIndex": 0, "SubnetId": "subnet-0abc", "Groups": ["sg-0abc"] },
    { "DeviceIndex": 1, "NetworkCardIndex": 1, "SubnetId": "subnet-0abc", "Groups": ["sg-0def"] }
  ]
}
```

## Common misconfigurations

| Misconfiguration | Symptom | Fix |
|---|---|---|
| `gp2` accepted from AMI default | 20% overpay, no IOPS tuning | Explicitly set `gp3` |
| `DeleteOnTermination=false` on non-root | Orphaned volumes | Set `true` for stateless |
| Top-level `SecurityGroupIds` + `NetworkInterfaces.Groups` | Top-level silently ignored | Use only `NetworkInterfaces.Groups` |
| `AssociatePublicIpAddress` on `DeviceIndex>0` | Silently ignored | Only works on index 0 |
| `ephemeralN` on non-`d` instance type | Silently ignored | Verify instance type has disks |
| IPv6 on subnet without IPv6 CIDR | Fails at launch | Assign IPv6 CIDR to VPC + subnet first |

## Expert heuristic: block device mapping — gp3 vs gp2 (moved from SKILL.md)

EBS `gp3` (2020+) is cheaper than `gp2` (~20%) and allows independent
IOPS/throughput tuning. A baseline model accepts the `gp2` default
from the AMI snapshot. Use `gp3` for all production volumes.

| Volume type | IOPS | Throughput | Price | When |
|---|---|---|---|---|
| `gp3` | 3,000 (tunable 16,000) | 125 MB/s (tunable 1,000) | ~20% cheaper | **Default** |
| `gp2` | Sized (3 IOPS/GB) | Tied to IOPS | Baseline | Legacy |
| `io2` | Up to 256,000 | Up to 4,000 MB/s | Premium | Databases |
| `st1`/`sc1` | n/a | Up to 500 MB/s | Cheapest | Data lakes / cold |

**DeleteOnTermination:** default is `true` for root, `false` for
non-root EBS volumes added via block device mapping — orphaned volumes
accumulate cost silently. Set explicitly to `true` on stateless.

**Instance store (`ephemeralN`):** only on instance types with
physical disks (`m5d`, `c5d`, `i3`, `x2ied`). Setting
`VirtualName=ephemeral0` on a type without disks is silently ignored.
