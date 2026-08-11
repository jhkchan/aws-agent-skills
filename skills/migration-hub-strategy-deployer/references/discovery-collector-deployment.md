# Discovery Collector Deployment Reference

Supplementary reference for the Migration Hub Strategy Deployer skill.
Use when deploying the Application Discovery Service Collector VM,
installing Discovery agents, or troubleshooting data collection gaps.

## Collector VM (agentless) deployment

The Collector VM is an OVA appliance deployed on vCenter or a
self-managed hypervisor. It gathers VM inventory and basic performance
without guest-level agents.

### Prerequisites checklist

| Prerequisite | Verification command | Effect if missing |
|---|---|---|
| vCenter 443 reachable from Collector | `nc -zv vcenter.example.com 443` | Cannot import inventory |
| AWS 443 reachable from Collector | `nc -zv migrationhub-strategy.us-east-1.amazonaws.com 443` | Cannot upload data |
| vCenter read credentials | Test login | Cannot enumerate VMs |
| Collector VM network (DHCP or static) | vCenter console | Cannot communicate |
| DNS resolution for AWS endpoints | `nslookup migrationhub-strategy.us-east-1.amazonaws.com` | Intermittent upload failures |
| Home region confirmed | `aws migrationhub-strategy get-portfolio-preferences` | Data lands in wrong region |

### Deployment steps

1. Download the Collector OVA from the Migration Hub console (Discovery
   > Tools > Discovery Collector).
2. Deploy the OVA on vCenter via the vSphere client (right-click a
   cluster > Deploy OVF Template).
3. Power on the Collector VM and note its IP address.
4. Access the Collector web UI via `https://<collector-ip>:443`.
5. Configure vCenter credentials and AWS home region in the Collector UI.
6. Start the collection. The Collector imports VM inventory and uploads
   to AWS periodically.

### Common Collector failures

| Failure | Root cause | Fix |
|---|---|---|
| Registered but not reporting | AWS 443 blocked by firewall | Open outbound 443 to `*.amazonaws.com` |
| Inventory empty | vCenter credentials wrong or read-only access missing | Verify vCenter role has `System.Read` on the vCenter object |
| Partial inventory | vCenter scope limited to one datacenter | Expand the vCenter scope in the Collector UI |
| Upload throttling | Network bandwidth constraint | Schedule uploads during off-peak hours in Collector settings |
| Collector VM disk full | OVA default disk size too small for large vCenter | Increase disk in vCenter before starting collection |

## Discovery Agent (agent-based) deployment

The Discovery Agent is installed on each guest OS to collect
process-level performance and network-connection data.

### Install commands by OS

| OS | Command |
|---|---|
| Amazon Linux 2 / RHEL | `sudo yum install aws-discovery-agent -y` |
| Ubuntu | `sudo apt-get install aws-discovery-agent -y` |
| Windows | Download and run the MSI installer from the Migration Hub console |
| SUSE | `sudo zypper install aws-discovery-agent -y` |

### Post-install verification

```bash
# Verify the agent is running and reporting
aws discovery describe-agents --region us-east-1

# Check agent health (Linux)
sudo systemctl status aws-discovery-agent

# Check agent health (Windows)
Get-Service AWSDiscoveryAgent
```

### Agent data depth vs Collector

| Data dimension | Agent | Collector VM |
|---|---|---|
| VM inventory | Yes | Yes |
| OS version (from guest) | Yes | No (from vCenter tools, may be stale) |
| Process-level CPU/memory | Yes | No |
| Per-process network connections | Yes | No |
| Inter-host dependency map | Yes | No |
| Disk I/O per process | Yes | No |

## Discovery data merge

When both agent-based and agentless data are present, Discovery merges
them. Agent data takes precedence for guest-level attributes (OS version,
processes, network). Collector data provides VM-level inventory for hosts
without agents.

The merge is automatic — no operator action required. However, the merge
has a 15-30 minute propagation delay. Newly installed agents may not
appear in the console immediately.
