# License Rules and Counting Types — License Manager Deployer

Deep reference on license counting types (vCPU, Instance, Core),
vendor-specific license rule syntax (Oracle Tenancy/HonorVcpuOptimization,
SQL Server coreFactor), and the relationship between counting type and
license rules. Loaded on demand by the skill — kept out of the main
SKILL.md body so the provisioning procedure stays scannable.

## Counting type fundamentals

### vCPU counting

vCPU counting measures total virtual CPUs across all running associated
instances. This is the counting type for Oracle Database and many per-
vCPU commercial products.

```text
Example: license count = 200 (vCPUs)
  Instance 1: m5.2xlarge (8 vCPU) → consumes 8
  Instance 2: m5.4xlarge (16 vCPU) → consumes 16
  Instance 3: m5.large (2 vCPU) → consumes 2
  Total consumed: 26 vCPUs out of 200
  Remaining: 174 vCPUs
```

**HonorVcpuOptimization rule:** when `HonorVcpuOptimization=true` and the
EC2 instance has thread scheduling enabled (default for most instance
types), License Manager treats 4 vCPUs as 1 license unit. This matches
Oracle's standard processor licensing model where 1 processor license =
2 cores, and a hyperthreaded core = 2 vCPUs.

```text
Without HonorVcpuOptimization:
  m5.2xlarge (8 vCPU) → consumes 8 license units

With HonorVcpuOptimization=true:
  m5.2xlarge (8 vCPU) → 8 vCPUs / 4 = 2 license units consumed
```

### Instance counting

Instance counting measures each running associated instance as 1 license
unit, regardless of instance size. This is the counting type for per-
instance software (some middleware, ISV tools).

```text
Example: license count = 50 (instances)
  10 instances running → consumes 10
  Remaining: 40 instances
```

Instance counting does NOT use vendor-specific license rules. The
`--license-rules` parameter is typically omitted for instance-based
configurations.

### Core counting

Core counting measures physical CPU cores (NOT vCPUs, NOT hyperthreaded
threads). This is the counting type for SQL Server and Windows Server
(core-based licensing).

```text
Example: license count = 24 (cores), coreFactor=0.5
  m5.2xlarge has 1 physical processor with 4 physical cores
  Consumed = 4 cores × 0.5 coreFactor = 2 license units
  m5.4xlarge has 2 physical processors with 4 cores each = 8 cores
  Consumed = 8 cores × 0.5 coreFactor = 4 license units
```

**coreFactor rule:** the core factor multiplies physical cores to compute
license consumption. SQL Server Standard uses 0.5; Enterprise uses 1.0.
Windows Server uses 0.5 for both Standard and Datacenter.

## Oracle Database license rules

Oracle Database uses vCPU counting with mandatory tenancy rules.

### Tenancy rule

| Tenancy value | Meaning | Use case |
|---|---|---|
| `Shared` | Instance runs on shared EC2 hardware (default) | Standard cloud deployment |
| `Instance` | Instance runs on a Dedicated Instance | Compliance requiring hardware isolation |
| `Host` | Instance runs on a Dedicated Host | Oracle BYOL with specific host licensing |

### HonorVcpuOptimization rule

| Value | Effect |
|---|---|
| `true` | Treats 4 vCPUs as 1 Oracle processor license (matches Oracle's licensing model) |
| `false` | Counts each vCPU as 1 license unit (does NOT match Oracle's standard model) |

**Recommendation:** always set `HonorVcpuOptimization=true` for Oracle
unless you have a specific reason not to. Oracle's standard licensing
model counts processors, not vCPUs, and 1 Oracle processor = 2 cores =
4 vCPUs (with hyperthreading).

### Oracle rule examples

```bash
# Oracle Standard Edition, shared tenancy, honor vCPU opt
LICENSE_RULES='Tenancy=Shared,HonorVcpuOptimization=true'

# Oracle Enterprise Edition on Dedicated Host (BYOL)
LICENSE_RULES='Tenancy=Host,HonorVcpuOptimization=true'

# Oracle on Dedicated Instance
LICENSE_RULES='Tenancy=Instance,HonorVcpuOptimization=true'
```

## SQL Server license rules

SQL Server uses core counting with the coreFactor rule.

### coreFactor rule

| Edition | coreFactor | Effect |
|---|---|---|
| Standard | `0.5` | 1 license = 2 physical cores |
| Enterprise | `1.0` | 1 license = 1 physical core |

### location rule

| location value | Meaning |
|---|---|
| `EC2` | Instance runs on EC2 shared hardware |
| `Host` | Instance runs on a Dedicated Host |

### SQL Server rule examples

```bash
# SQL Server Standard, EC2, 0.5 core factor
LICENSE_RULES='location=EC2,coreFactor=0.5'

# SQL Server Enterprise, EC2, 1.0 core factor
LICENSE_RULES='location=EC2,coreFactor=1.0'

# SQL Server Standard on Dedicated Host
LICENSE_RULES='location=Host,coreFactor=0.5'
```

## Windows Server license rules

Windows Server also uses core counting:

```bash
# Windows Server Standard, EC2, 0.5 core factor
LICENSE_RULES='location=EC2,coreFactor=0.5'

# Windows Server Datacenter, EC2, 0.5 core factor (unlimited VMs per host)
LICENSE_RULES='location=EC2,coreFactor=0.5'
```

## Enforcement behavior

### Hard limit (enforce=true)

When the license configuration has `LicenseRulesEnforce=true`, License
Manager BLOCKS any new EC2 instance launch that would cause the license
count to be exceeded. The launch fails with an error referencing the
license configuration.

```bash
# Hard limit — blocks non-compliant launches
aws license-manager create-license-configuration \
  --name "oracle-hard" \
  --license-counting-type vCPU \
  --license-count 200 \
  --license-rules 'Tenancy=Shared,HonorVcpuOptimization=true' \
  --license-rules-enforce
```

### Soft limit (enforce=false)

When the license configuration has `LicenseRulesEnforce=false`, License
Manager does NOT block launches. It only emits a violation event when
the count is exceeded. This is for monitoring-only scenarios.

```bash
# Soft limit — alert only, does not block
aws license-manager create-license-configuration \
  --name "oracle-soft" \
  --license-counting-type vCPU \
  --license-count 200 \
  --license-rules 'Tenancy=Shared,HonorVcpuOptimization=true'
  # --license-rules-enforce omitted (defaults to false)
```

## Common counting mistakes

### Mistake 1: Wrong counting type for the vendor

Oracle with Core counting, or SQL Server with vCPU counting, produces
non-compliant tracking. Always match:
- Oracle → vCPU
- SQL Server → Core
- Per-instance software → Instance

### Mistake 2: Missing coreFactor for SQL Server

Creating a SQL Server config without `coreFactor` means License Manager
counts raw physical cores with no factor applied — typically resulting
in over-counting and premature license exhaustion.

### Mistake 3: HonorVcpuOptimization=false for Oracle

Setting `HonorVcpuOptimization=false` means each vCPU counts as 1
license unit. For an m5.2xlarge (8 vCPU), this consumes 8 licenses
instead of the correct 2 (with optimization). This causes massive
over-counting.

## Terraform examples

```hcl
# Oracle Database — vCPU counting, shared tenancy
resource "aws_licensemanager_license_configuration" "oracle" {
  name                             = "oracle-db-vcpu"
  license_counting_type            = "vCPU"
  license_count                    = 200
  license_rules                    = ["Tenancy=Shared", "HonorVcpuOptimization=true"]
  license_configuration_description = "Oracle DB Standard Edition vCPU tracking"

  tags = {
    Vendor      = "Oracle"
    Environment = "production"
  }
}

# SQL Server — core counting, 0.5 core factor
resource "aws_licensemanager_license_configuration" "sqlserver" {
  name                             = "sqlserver-std-core"
  license_counting_type            = "Core"
  license_count                    = 24
  license_rules                    = ["location=EC2", "coreFactor=0.5"]
  license_configuration_description = "SQL Server Standard Edition core tracking"

  tags = {
    Vendor      = "SQLServer"
    Environment = "production"
  }
}

# Associate with launch template
resource "aws_launch_template" "oracle_workload" {
  name                   = "oracle-workload"
  image_id               = "ami-xxx"
  instance_type          = "m5.2xlarge"

  license_specification {
    license_configuration_arn = aws_licensemanager_license_configuration.oracle.arn
  }
}
```
