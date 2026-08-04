# EC2 Security Group Exposure Reference Guide

Supplementary reference for the EC2 Security-Group Auditor skill.

## High-risk port registry (critical when PUBLIC)

### Administrative access
| Port(s) | Protocol | Service | Risk |
| --- | --- | --- | --- |
| 22 | TCP | SSH | Brute-force target #1 — botnets scan within minutes |
| 23 | TCP | Telnet | Unplaintext credentials; trivially exploitable |
| 3389 | TCP/UDP | RDP | Brute-force / BlueKeep-class exploit target |
| 5900-5910 | TCP | VNC | Often deployed with no auth; trivial takeover |
| 2375 | TCP | Docker daemon (no TLS) | Unauthenticated container RCE; full host compromise |
| 2376 | TCP | Docker daemon (TLS) | Still RCE if credentials compromised |

### Databases
| Port(s) | Protocol | Service | Risk |
| --- | --- | --- | --- |
| 3306 | TCP | MySQL / Aurora MySQL | Data exfiltration, ransomware |
| 5432 | TCP | PostgreSQL / Aurora PG | Data exfiltration, ransomware |
| 1433 | TCP | MSSQL / SQL Server | Data exfiltration; SA brute-force |
| 1521 | TCP | Oracle TNS | Data exfiltration; TNS poisoning |
| 27017-27019 | TCP | MongoDB | NoSQL ransomware (default no-auth history) |
| 6379 | TCP | Redis | In-memory DB — cryptomining, data exfil, ransomware |
| 9042 | TCP | Cassandra CQL | NoSQL data exfiltration |
| 5984 | TCP | CouchDB | Default "admin party" on old versions |
| 11211 | TCP/UDP | Memcached | UDP amplification DDoS (~51,000×); data exfil |
| 9200 | TCP | Elasticsearch HTTP | Data exfil + ransomware |
| 9300 | TCP | Elasticsearch transport | Cluster-level compromise |

### Message queues / streaming
| Port(s) | Protocol | Service | Risk |
| --- | --- | --- | --- |
| 5671, 5672 | TCP | AMQP / RabbitMQ | Queue manipulation; message exfil |
| 9092 | TCP | Kafka | Topic read/write; data tampering |

### Container orchestration
| Port(s) | Protocol | Service | Risk |
| --- | --- | --- | --- |
| 6443 | TCP | Kubernetes API server | Full cluster takeover |
| 10250 | TCP | Kubelet API | Per-node RCE; pod creation |
| 2379, 2380 | TCP | etcd | K8s control-plane state; cluster root |

### Windows / RPC
| Port(s) | Protocol | Service | Risk |
| --- | --- | --- | --- |
| 135 | TCP | MS-RPC endpoint mapper | Remote procedure call abuse |
| 139 | TCP | NetBIOS Session | WannaCry / EternalBlue lateral movement |
| 445 | TCP | SMB / CIFS | WannaCry; EternalBlue; ransomware spread |
| 593 | TCP | HTTP RPC | RPC over HTTP abuse |

### Directory services
| Port(s) | Protocol | Service | Risk |
| --- | --- | --- | --- |
| 389 | TCP | LDAP | Directory enumeration; credential theft |
| 636 | TCP | LDAPS | Directory enumeration (even over TLS) |
| 3268 | TCP | AD Global Catalog | Full forest enumeration |
| 9389 | TCP | AD DS Web Services | AD management exposure |

### Email
| Port(s) | Protocol | Service | Risk |
| --- | --- | --- | --- |
| 25 | TCP | SMTP | Open-relay spam; reputation damage |

### Maximum exposure
| Port(s) | Protocol | Service | Risk |
| --- | --- | --- | --- |
| 0-65535 | TCP | All TCP ports | Every service directly attackable |
| All (-1) | ALL | All protocols | TCP + UDP + ICMP + SCTP; worst case |

### Non-critical (PUBLIC_NONCRITICAL when PUBLIC)
| Port(s) | Protocol | Service | Notes |
| --- | --- | --- | --- |
| 80 | TCP | HTTP | Acceptable behind ALB; verify redirect to 443 |
| 443 | TCP | HTTPS | Acceptable for web-facing tiers behind ALB/WAF |
| 8080 | TCP | alt HTTP | Acceptable behind ALB; verify not admin panel |

## CIDR / Source classification

| Source | Classification | Notes |
| --- | --- | --- |
| `0.0.0.0/0` | PUBLIC (IPv4 internet) | All IPv4 addresses |
| `::/0` | PUBLIC (IPv6 internet) | All IPv6 addresses |
| `0.0.0.0/1` + `128.0.0.0/1` | PUBLIC (split-horizon) | Union covers all IPv4; each is PUBLIC |
| `10.0.0.0/7` | PUBLIC (partial) | Includes `11/8` which is NOT RFC 1918 |
| `10.0.0.0/8` | RESTRICTED (RFC 1918) | Private |
| `172.16.0.0/12` | RESTRICTED (RFC 1918) | Private |
| `192.168.0.0/16` | RESTRICTED (RFC 1918) | Private |
| `100.64.0.0/10` | RESTRICTED (CGNAT, RFC 6598) | Shared carrier-grade NAT; flag for review |
| `sg-xxxxxxxx` | RESTRICTED (SG reference) | Traffic from ENIs with that SG |
| `pl-xxxxxxxx` | CONDITIONAL | AWS-managed lists may contain public IPs; inspect contents |
| Specific IP `/32` | RESTRICTED (single source) | Narrow; not "private" but not internet-wide |

## Classification decision tree (per-rule, then aggregate)

```
For EACH inbound rule:
  1. Classify SOURCE (PUBLIC / RESTRICTED / CONDITIONAL)
  2. Classify PORT/PROTOCOL (critical / non-critical / N/A)
  3. Assign per-rule verdict:
     PUBLIC + critical port/range/protocol  -> OPEN
     PUBLIC + non-critical port             -> PUBLIC_NONCRITICAL
     RESTRICTED + anything                  -> RESTRICTED
     No rules                               -> RESTRICTED

Aggregate SG verdict = WORST per-rule verdict:
  OPEN > PUBLIC_NONCRITICAL > RESTRICTED
```

### Port range intersection rules

- `20-25` contains 22 (SSH) and 25 (SMTP) -> intersects high-risk -> OPEN if PUBLIC
- `3300-3400` contains 3306 (MySQL) -> intersects high-risk -> OPEN if PUBLIC
- `440-450` contains 443 only (non-critical) -> does NOT intersect high-risk -> PUBLIC_NONCRITICAL if PUBLIC
- `0-65535` contains all high-risk ports -> always OPEN if PUBLIC

## Remediation patterns

### SSH (port 22)
- **Preferred:** Remove inbound SSH rule entirely. Use AWS Systems Manager
  Session Manager for shell access — no open ports, IAM-authenticated,
  fully audited.
- **Fallback:** Restrict to a bastion host security group ID
  (`sg-xxxxxxxx`) rather than a CIDR.

### Databases (3306, 5432, 1433, 1521, 27017, 6379, 9042, 5984, 11211, 9200)
- Restrict the source to the application-tier security group ID only.
- Database subnets should have no internet gateway route (private subnet).

### Elasticsearch (9200, 9300)
- Restrict to ingestion SG + dashboard SG only.
- Transport port (9300) should never leave the cluster peer set.

### Docker daemon (2375, 2376)
- Never expose to the internet. Bind to localhost or private VPN.
- Enable TLS client cert auth on 2376 if remote access is unavoidable.

### Kubernetes (6443, 10250, 2379-2380)
- 6443 (API server): restrict to control-plane + operator CIDRs. P0.
- 10250 (Kubelet): restrict to control-plane only.
- 2379-2380 (etcd): restrict to control-plane only.

### All-ports rules (0-65535, protocol -1)
- Delete entirely. Recreate with only the specific ports the workload
  requires. An all-ports rule from `0.0.0.0/0` is the AWS equivalent of
  disabling the firewall.

### Web tiers (80, 443)
- Public HTTPS/HTTP is acceptable for web-facing tiers behind a load
  balancer or WAF. Verify the listener points to an ALB/NLB, not directly
  to an instance. The backend SG should reference the ALB SG ID, not
  `0.0.0.0/0`.

### ICMP
- Restrict to a known monitoring CIDR. Never allow ICMP ALL (`-1`)
  from `0.0.0.0/0` — enables ping sweeps, OS fingerprinting, Smurf.

### Memcached over UDP
- Disable UDP entirely unless explicitly required.
- UDP amplification factor is ~51,000× for DDoS reflection attacks.
