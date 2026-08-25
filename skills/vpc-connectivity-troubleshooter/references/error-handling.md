# Error Handling — VPC Connectivity Troubleshooter

Pre-flight safety checks and per-LAYER remediation guidance moved out of the SKILL.md body. Loaded on demand.

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`authorize-security-group-ingress`, `create-network-acl-entry`,
  `create-route`, `modify-vpc-endpoint`, `accept-vpc-peering-
  connection`), emit and await operator approval.

- **Read-only first.** Every probe in the diagnostic tree is
  read-only (`describe-*`, `dig`, `nc -vz`, Reachability Analyzer).
  Do not perform state-changing operations as diagnostic probes.

- **SG changes should prefer CIDR over specific IP** for tolerance to
  instance moves within the subnet, but never expand the scope to
  `0.0.0.0/0` to "fix" a connectivity issue.

- **NACL changes are not stateful.** Adding an inbound rule requires
  a matching outbound rule on the ephemeral range for the return
  traffic. Always update both directions.

- **Route table changes affect every subnet using the table.** A
  VPC-wide main route table change affects every subnet that does not
  have an explicit subnet-level table. Verify scope before applying.

- **VPC peering accept changes the accepter's network exposure.**
  Accepting a peering connection allows the requester's VPC to reach
  the accepter's VPC per the route table. Confirm the route table
  scope before accepting.

- **Transit Gateway route changes affect every attachment using the
  table.** Verify the TGW route table's association and propagation
  scope before modifying.

- **VPC endpoint policy changes affect every VPC using the endpoint.**
  Tighten gradually; never deny-by-default without confirming no
  workload depends on the denied action.

- **Bulk remediation batch limit.** If the diagnosis identifies the
  same root cause across multiple subnets/instances (e.g., a missing
  NACL outbound rule), batch remediation into groups of at most 5
  resources, emit a single CONFIRM per batch, and verify between
  batches.

## Remediation guidance (per LAYER)

### For ROUTE_TABLE_MISSING — no route for destination

```bash
aws ec2 create-route --route-table-id <rtb> \
  --destination-cidr-block <dest-cidr> \
  --vpc-peering-connection-id <pcx>   # for peered VPC
  # --transit-gateway-id <tgw>         # for TGW
  # --gateway-id <igw-xxx>             # for internet (with public IP)
  # --nat-gateway-id <nat-xxx>         # for internet (private)
```

Verify both source and destination route tables have the corresponding
route.

### For ROUTE_TABLE_WRONG_TARGET — wrong route target

Replace the route with the correct target:

```bash
aws ec2 replace-route --route-table-id <rtb> \
  --destination-cidr-block <dest-cidr> \
  --nat-gateway-id <nat-xxx>   # or other correct target
```

### For ROUTE_OVERLAPPING_CIDR — silent peering failure

- Renumber one VPC to a non-overlapping CIDR (major change; plan a
  maintenance window).
- Or migrate connectivity to Transit Gateway with PrivateLink overlay
  (translation).

### For SG_INBOUND — missing or mis-scoped inbound rule

```bash
aws ec2 authorize-security-group-ingress --group-id <sg> \
  --protocol tcp --port <port> --cidr <source-cidr>
```
Prefer a referenced SG (same-VPC) or prefix list over a raw CIDR.
Verify with `nc -vz`.

### For SG_OUTBOUND — missing source-side egress

Same pattern, on the source SG. The default egress is allow-all; if
the egress was tightened, restore the necessary scope.

### For SG_REFERENCE_CROSS_VPC — dead SG reference

Replace the cross-VPC SG reference with:
- A CIDR block matching the source's peered-VPC subnet, OR
- A referenced SG in the peered VPC (with peering in the route table).

### For NACL_STATELESS — missing ephemeral rule

Add the inbound rule on the listener port from the source CIDR. Add
the outbound rule on the ephemeral port range (1024-65535) to the
source CIDR. Verify with `nc -vz`.

### For DNS_RESOLUTION — VPC DNS settings

```bash
aws ec2 modify-vpc-attribute --vpc-id <vpc-id> \
  --enable-dns-support
aws ec2 modify-vpc-attribute --vpc-id <vpc-id> \
  --enable-dns-hostnames
```

### For DNS_PHZ_ASSOCIATION — PHZ not associated

Associate the PHZ with the consumer VPC:

```bash
aws route53 associate-vpc-with-hosted-zone \
  --hosted-zone-id <hz-id> \
  --vpc VPCRegion=<region>,VPCId=<vpc-id>
```

For cross-account, use Shared VPC or a Route 53 Resolver Rule.

### For ENDPOINT_POLICY — endpoint policy blocking

```bash
aws ec2 modify-vpc-endpoint --vpc-endpoint-id <vpce> \
  --policy-document '<JSON with the necessary Allow>'
```

### For PEERING_INACTIVE — peering not active

Accept the peering on the accepter side:

```bash
aws ec2 accept-vpc-peering-connection \
  --vpc-peering-connection-id <pcx>
```

### For PEERING_DNS_RESOLUTION — remote DNS flag false

The flag is set at peering creation; to enable on an existing
peering:

```bash
aws ec2 modify-vpc-peering-connection-options \
  --vpc-peering-connection-id <pcx> \
  --requester-peering-connection-options \
    AllowDnsResolutionFromRemoteVpcDomainName=true
```

Both VPCs must have `enableDnsSupport` and `enableDnsHostnames` true.

### For PEERING_SG_REFERENCE — dead cross-VPC SG reference

Replace with a CIDR or a referenced SG in the peered VPC.

### For TGW_ROUTE_PROPAGATION — routes not propagating

```bash
aws ec2 enable-transit-gateway-route-table-propagation \
  --transit-gateway-route-table-id <tgw-rtb> \
  --transit-gateway-attachment-id <attachment-id>
```

### For TGW_ASSOCIATION_MISSING — attachment not associated

```bash
aws ec2 associate-transit-gateway-route-table \
  --transit-gateway-route-table-id <tgw-rtb> \
  --transit-gateway-attachment-id <attachment-id>
```

### For PRIVATELINK_ENDPOINT_SERVICE — provider-side issue

Restore the NLB and listener; verify target health in the consumer's
AZ.

### For PRIVATELINK_SG — endpoint SG missing

Add an inbound rule to the endpoint's SG:

```bash
aws ec2 authorize-security-group-ingress --group-id <endpoint-sg> \
  --protocol tcp --port <listener-port> --cidr <source-cidr>
```
