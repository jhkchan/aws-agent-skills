# RDS Connectivity Troubleshooter — advanced patterns (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

## Expert heuristic (moved from SKILL.md)

> **Security group rules are bidirectional.** Every RDS connection
> timeout is a packet dropped somewhere. The drop is either: (a) the
> RDS SG lacks an inbound rule allowing the client's SG / CIDR on the
> DB port; (b) the client SG lacks an outbound rule allowing the RDS
> endpoint on the DB port; (c) a NACL on either subnet; or (d) a route
> table missing the VPC peering / TGW route. The order is
> deterministic: check the RDS SG inbound FIRST (most common), then
> the client SG egress, then NACLs, then route tables. Operators who
> skip the client-side egress check waste hours.
>
> **Aurora writer vs reader endpoint routing matters.** Aurora exposes
> a `writer` endpoint (always points at the writer), a `reader`
> endpoint (round-robins across readers), and per-instance endpoints.
> The legacy "cluster endpoint" follows the writer after failover but
> has DNS-update lag. A write that hits a reader throws
> `cannot execute INSERT in a read-only transaction`. Route writes to
> the writer endpoint; route reads to the reader endpoint. Mixing the
> two is the most common Aurora application error.
>
> **`storage-full` means storage auto-scaling was not enabled (or the
> maximum storage threshold was hit).** When an RDS instance exhausts
> its allocated storage, it stops accepting writes — the application
> sees connection errors and query timeouts. The status shows
> `StorageStatus: storage-full`. The fix is enabling storage
> auto-scaling (`--storage-auto-scaling --max-allocated-storage <N>`)
> or manually allocating more storage. Raising `max_connections` or
> upsizing the instance class does nothing — the bottleneck is disk,
> not compute.

## Configuration dependency graph (moved from SKILL.md)

```
                   RDS / Aurora instance
                          │
        ┌─────────────────┼──────────────────┐
        ▼                 ▼                  ▼
   VPC security     DB subnet group     parameter group
   groups           (subnets in AZs,    (max_connections,
   (RDS SG            each in VPC)       force_ssl, etc.)
   inbound +                                   │
   client SG                                    ▼
   egress)                                  option group
                          │                 (engine options,
                          ▼                  TLS, native auth)
                   instance status
                   (available /                  │
                    storage-full /               ▼
                    modifying /              IAM DB auth
                    failing-over)            (rds-db:connect
                          │                  policy + DB user
                          ▼                  with AWSAuthentication
                   endpoint                  Plugin)
                   (writer /                        │
                    reader /                        ▼
                    custom /                    Aurora global
                    instance)                   database primary
                          │                          │
                          ▼                          ▼
                   DNS resolution              secondary cluster
                   (Route 53 CNAME,            (replication lag,
                    on-prem DNS,               cross-region)
                    cross-region)
```

Read top-down: a connectivity failure is a broken edge or broken node
in this graph. The diagnostic tree walks the graph from the symptom
down.

