# Eval prompt: collector-network-blocker

Diagnose why the following Collector deployment is not reporting data.
Emit the standard ASSESSMENT block with the root cause in the GAP field.

Design reference: collector-network-blocker
Account: 111111111111
Home region: us-east-1
vCenter: vcenter.example.com

Portfolio: 80 VMs.
Discovery: agentless Collector VM deployed on vCenter.
Collector status: registered but not reporting data.
Network test: vCenter 443 reachable, AWS 443 BLOCKED by on-prem firewall.
Agent-based: not deployed.
