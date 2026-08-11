# Eval prompt: eol-os-anti-pattern

Design a migration assessment for the following portfolio, paying
particular attention to anti-pattern detection and wave sequencing.
Emit the standard ASSESSMENT block.

Design reference: eol-os-anti-pattern
Account: 111111111111
Home region: us-east-1

Portfolio: 50 servers.
Discovery: agent-based on all 50 hosts, 14-day collection window.
Anti-pattern: Windows Server 2012 R2 on srv-001, srv-002, srv-003.
Dependencies: srv-001 and srv-002 form a connected cluster with shared-dns.
MGN: configured. DMS: not needed (no databases).
