# Authentication and Authorization — Client VPN Endpoint Deployer

Deep reference on Client VPN authentication (mutual TLS via ACM,
Active Directory, SAML 2.0 federation), authorization rules (network
CIDR + group access, first-match-wins ordering), certificate lifecycle
and revocation (CRL), and self-service portal enablement. Loaded on
demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Authentication types

### Mutual TLS (certificate-mutual-auth)

The most traditional Client VPN auth. A server certificate (imported
into ACM) establishes the TLS tunnel; client certificates (signed by
the same CA) authenticate individual clients.

**Prerequisites:**

1. A Certificate Authority (CA) — can be AWS Private Certificate
   Authority or an external CA.
2. A server certificate signed by the CA, imported into ACM.
3. Client certificates signed by the same CA, distributed to each
   client.

```bash
# Create the endpoint with mutual TLS
aws ec2 create-client-vpn-endpoint \
  --client-cidr-block 10.250.0.0/16 \
  --server-certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/abc123 \
  --authentication-type certificate-mutual-auth \
  --region us-east-1
```

**Certificate generation (OpenVPN easy-rsa):**

```bash
# Generate server and client certificates using easy-rsa
./easyrsa init-pki
./easyrsa build-ca nopass
./easyrsa build-server-full server nopass
./easyrsa build-client-full client1 nopass

# Import server certificate to ACM
aws acm import-certificate \
  --certificate file://server.crt \
  --private-key file://server.key \
  --certificate-chain file://ca.crt \
  --region us-east-1
```

### Active Directory (directory-service-auth)

Clients authenticate against AWS Managed Microsoft AD or Simple AD.

**Prerequisites:**

1. An AWS Directory Service directory (Managed AD or Simple AD).
2. The directory must be accessible from the VPC where the Client VPN
   is deployed.

```bash
aws ec2 create-client-vpn-endpoint \
  --client-cidr-block 10.250.0.0/16 \
  --server-certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/abc123 \
  --authentication-type directory-service-auth \
  --directory-id d-9067a4a4bd \
  --region us-east-1
```

**Note:** A server certificate in ACM is STILL required even for AD
auth — it secures the TLS tunnel. The AD handles user authentication;
the cert handles transport encryption.

### SAML 2.0 federation (federated-authentication)

Clients authenticate via a SAML IdP (Okta, Azure AD, Google
Workspace, etc.). Enables SSO.

**Prerequisites:**

1. An IAM SAML provider in AWS.
2. An IAM role that the VPN client assumes after SAML authentication.
3. The SAML metadata document from the IdP.

```bash
aws ec2 create-client-vpn-endpoint \
  --client-cidr-block 10.250.0.0/16 \
  --server-certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/abc123 \
  --authentication-type federated-authentication \
  --saml-provider-arn arn:aws:iam::123456789012:saml-provider/CorporateIdP \
  --region us-east-1
```

**Federated authorization:** with SAML, the IdP controls group
membership. Authorization rules reference the SAML groups to determine
network access.

## Multiple authentication types

Client VPN supports enabling multiple auth types simultaneously:

- Mutual TLS + SAML
- Mutual TLS + Active Directory

This is useful for mixed fleets (e.g., machine certs for CI/CD, SAML
for human users).

## Authorization rules

### First-match-wins evaluation

Authorization rules are evaluated in ORDER. The first rule that
matches a connected user determines their access. This is critical for
rule design.

```text
Rule creation order matters:
  Rule 1 (created first): CIDR 10.0.0.0/16 → group data-team
  Rule 2 (created second): CIDR 0.0.0.0/0 → all groups

  User "alice" in data-team:
    → Connects → Rule 1 evaluated → matches (data-team, 10.0.0.0/16)
    → alice gets access to 10.0.0.0/16 only
    → Rule 2 is NOT evaluated for alice

  User "bob" in all-staff (not data-team):
    → Connects → Rule 1 evaluated → does not match (bob not in data-team)
    → Rule 2 evaluated → matches (all-staff, 0.0.0.0/0)
    → bob gets access to everything
```

### Creating rules in the correct order

There is NO reorder API. To change rule order, delete and recreate:

```bash
# Delete a rule (must specify the destination CIDR)
aws ec2 revoke-client-vpn-ingress \
  --client-vpn-endpoint-id cvpn-xxx \
  --target-network-cidr 0.0.0.0/0 \
  --region us-east-1

# Recreate in the correct position
aws ec2 authorize-client-vpn-ingress \
  --client-vpn-endpoint-id cvpn-xxx \
  --target-network-cidr 0.0.0.0/0 \
  --authorize-all-groups \
  --region us-east-1
```

### Default allow-all rule

The simplest authorization rule grants all authenticated users access
to the VPC CIDR:

```bash
aws ec2 authorize-client-vpn-ingress \
  --client-vpn-endpoint-id cvpn-xxx \
  --target-network-cidr 10.0.0.0/16 \
  --authorize-all-groups \
  --description "Default allow-all to VPC" \
  --region us-east-1
```

### Group-restricted rule

For SAML or AD, restrict access by group:

```bash
aws ec2 authorize-client-vpn-ingress \
  --client-vpn-endpoint-id cvpn-xxx \
  --target-network-cidr 0.0.0.0/0 \
  --access-group-id sg-vpn-full-access \
  --description "Full access for full-access group" \
  --region us-east-1
```

## Certificate revocation (CRL)

Mutual TLS revocation uses a Certificate Revocation List (CRL)
uploaded to the endpoint. There is no per-certificate revoke API.

```bash
# Generate a CRL (using easy-rsa or openssl)
openssl ca -gencrl -out crl.pem -config openssl.cnf

# Upload the CRL to the endpoint
aws ec2 import-client-vpn-client-certificate-revocation-list \
  --client-vpn-endpoint-id cvpn-xxx \
  --certificate-revocation-list file://crl.pem \
  --region us-east-1
```

**CRL lifecycle:** the CRL must be regenerated and re-uploaded each
time a certificate is revoked. Set up an automated pipeline for this.

## Self-service portal

The self-service portal provides a web URL where users download their
VPN client configuration. Enabled per endpoint.

```bash
# Enable during creation
aws ec2 create-client-vpn-endpoint \
  --client-portal-enabled enabled \
  ...

# Retrieve the portal URL
aws ec2 describe-client-vpn-endpoints \
  --client-vpn-endpoint-ids cvpn-xxx \
  --query 'ClientVpnEndpoints[0].SelfServicePortalUrl' \
  --region us-east-1 --output text
```

The portal URL looks like:
`https://self-service.clientvpn.amazonaws.com/<endpoint-id>/`

Users visit the URL, authenticate (via SAML or by providing their
client certificate), and download the OpenVPN configuration file.

## Terraform example

```hcl
# Client VPN endpoint with mutual TLS
resource "aws_ec2_client_vpn_endpoint" "main" {
  description            = "Corporate Client VPN"
  client_cidr_block      = "10.250.0.0/16"
  server_certificate_arn = aws_acm_certificate.server.arn
  authentication_options {
    type                       = "certificate-mutual-auth"
    root_certificate_chain_arn = aws_acm_certificate.ca.arn
  }
  connection_log_options {
    enabled               = true
    cloudwatch_log_group  = aws_cloudwatch_log_group.vpn.name
  }
  dns_servers    = ["10.0.0.2"]
  split_tunnel   = true
  transport_protocol = "udp"
  vpn_port       = 443

  tags = {
    Environment = "production"
  }
}

# Target subnet association
resource "aws_ec2_client_vpn_network_association" "main" {
  client_vpn_endpoint_id = aws_ec2_client_vpn_endpoint.main.id
  subnet_id              = aws_subnet.private.id
}

# Authorization rule (allow all to VPC)
resource "aws_ec2_client_vpn_authorization_rule" "allow_all" {
  client_vpn_endpoint_id = aws_ec2_client_vpn_endpoint.main.id
  target_network_cidr    = "10.0.0.0/16"
  authorize_all_groups   = true
}
```

## Expert heuristic: mutual TLS certificate-based auth revocation

With mutual TLS, client certificates are issued by a CA registered in
ACM. Revoking a client certificate requires uploading a CRL
(Certificate Revocation List) to the endpoint — there is no
per-certificate revoke API.

```text
Mutual TLS auth flow:
  1. Server certificate (ACM) → endpoint (server side)
  2. Client certificates signed by same CA → distributed to clients
  3. To revoke: generate CRL, upload via import-client-vpn-client-certificate-revocation-list

  aws ec2 import-client-vpn-client-certificate-revocation-list \
    --client-vpn-endpoint-id cvpn-xxx \
    --certificate-revocation-list file://crl.pem
```

**Key implication:** plan for certificate lifecycle management. For
large fleets, SAML federation is often simpler than managing
individual client certificates and CRLs.
