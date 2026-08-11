# Eval prompt: agentless-only-short-window

Audit the following migration assessment setup and identify any gaps
that would block a reliable assessment. Emit the standard ASSESSMENT
block.

Design reference: agentless-only-short-window
Account: 111111111111
Home region: us-east-1
vCenter: vcenter.example.com

Portfolio: 200 VMs in vCenter.
Discovery: agentless only (Collector VM deployed, no agents installed).
Collection window: 2 days.
Dependencies: unknown (no agent data).
MGN service role: not yet configured.
DMS: not yet configured.
