# Advanced Patterns (load on demand) — Directory Service Deployer

Expert heuristics (AD Connector vs Managed AD routing, Multi-Region replication conflict resolution, stub zone vs conditional forwarder) and Step 12 recent features moved verbatim from SKILL.md.
The Steps 1-11 decision logic, prerequisites checklist, output contract, and NEVER list remain in SKILL.md.

---

## Expert heuristic: AD Connector vs Managed AD routing (moved from SKILL.md)

A baseline model says "pick Managed AD." The correct heuristic
recognizes that the directory type depends on where the source of
truth lives and what features are needed.

```text
Where is the authoritative AD?
  ├── On-premises AD (source of truth)
  │     └── Need AWS app auth without replicating AD?
  │           ├── YES → AD Connector (proxy; on-prem stays authoritative)
  │           └── NO  → Managed AD with forest trust to on-prem AD
  ├── No existing AD (greenfield)
  │     └── Managed Microsoft AD
  │           ├── Standard  — up to 5,000 users
  │           └── Enterprise — up to 50,000+; supports Multi-Region replication
  └── Basic needs (no trust, no LDAPS, small scale)
        └── Simple AD (Small ~500 users, Large ~5,000 users)
              Constraints: NO trusts, NO LDAPS, NO Seamless Domain Join
```

**Key implication:** AD Connector is NOT a directory — it is a proxy.
If on-prem AD is unavailable, AD Connector cannot authenticate.
Managed AD is standalone and operates independently.

---

## Expert heuristic: Multi-Region replication conflict resolution (moved from SKILL.md)

Multi-Region replication is one-way (PRIMARY-to-REPLICA). A baseline
model assumes failover is a simple promotion. The expert knows that
conflict resolution during failover and re-convergence is the danger
zone.

```text
Failover scenario (primary us-east-1 → replica us-west-2):
  1. Promote us-west-2 replica to primary (manual API call)
  2. us-east-1 is now STALE — writes that happened after the last
     replication sync are LOST (RPO = replication lag, typically < 60s)
  3. When us-east-1 comes back, it CANNOT auto-rejoin as primary
     → must be re-added as a REPLICA of the new primary
     → conflicting writes on the old primary are discarded

Conflict resolution rules:
  ├── Last-writer-wins on the NEW primary's timeline
  ├── Old-primary unreplicated writes → silently dropped
  └── No merge logic — this is NOT multi-master

Expert rules:
  1. Document the RPO gap: replication lag = data loss window
  2. After failover, NEVER write to the old primary until it is
     re-added as a replica (split-brain causes irrecoverable conflict)
  3. Test failover at least quarterly — promotion + re-add is a
     multi-step manual process that fails under stress if untested
```

**Key implication:** Multi-Region replication is NOT active-active.
It is asynchronous one-way copy with manual failover. Treat the RPO
window as potential data loss and rehearse the failover runbook.

---

## Expert heuristic: DNS forwarder — stub zone vs conditional forwarder (moved from SKILL.md)

A baseline model treats all cross-domain DNS as "conditional
forwarders." AWS Directory Service supports both conditional
forwarders AND stub zones, and choosing the wrong one causes
resolution failures in multi-domain trust topologies.

```text
Conditional forwarder (aws ds create-conditional-forwarder):
  ├── Forwards queries for ONE specific domain suffix
  │     e.g., corp.example.com → 10.0.1.53
  ├── Resolves ONLY that suffix (not sub-domains of other forests)
  └── Must be recreated on EACH directory independently

Stub zone (via Microsoft DNS console on the domain controller):
  ├── Resolves an ENTIRE zone and follows referrals
  ├── Maintains a list of NS servers, updates dynamically
  └── Better for complex multi-forest topologies with delegation

Decision rule:
  ├── Single remote domain → conditional forwarder (simpler, API-native)
  ├── Multi-forest with delegation → stub zone (follows NS chain)
  └── AD Connector → conditional forwarder is the ONLY option
        (stub zones require domain controller access, which AD
        Connector does not provide)
```

**Key implication:** Conditional forwarders are API-managed and
directory-type-agnostic. Stub zones require direct domain controller
access and are NOT available for AD Connector. For Simple AD, only
conditional forwarders work. Match the DNS strategy to the directory
type and topology complexity.

---

## Step 12 — Recent features (moved from SKILL.md)

- **IAM Identity Center deep integration (2023-2024):** Enhanced
  integration with automated user provisioning and group sync.

- **Multi-Region replication improvements (2023-2024):** Faster
  replication convergence and improved failover tooling for
  Enterprise edition.

- **LDAPS for DC replication (2024-2025):** Extended LDAPS support to
  domain controller-to-controller replication for end-to-end
  encryption.

- **Directory sharing with AWS Organizations (2024-2025):**
  Simplified bulk sharing across accounts in an organization unit.

- **Password policy enforcement improvements (2025-2026):** Real-time
  validation and custom password filters for Managed Microsoft AD.
