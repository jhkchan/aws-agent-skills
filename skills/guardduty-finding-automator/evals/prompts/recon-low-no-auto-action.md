# Eval prompt: recon-low-no-auto-action

Design an automated GuardDuty response workflow for the following finding.
Emit the standard AUTOMATION block.

Design reference: recon-low-no-auto-action
Account: 111111111111
Region: us-east-1

GuardDuty finding type: Recon:EC2/PortProbeUnprotectedPort
Severity: 2.0 (LOW)
Sample resource: i-0webfrontend01 (port 22 probed from 198.51.100.50)
Authorized scanner: 198.51.100.50 (internal vulnerability scanner)
