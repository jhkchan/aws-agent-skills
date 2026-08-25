# Advanced Patterns — Roles Anywhere Trust Deployer

Deep-dive material moved out of the SKILL.md body so the procedure stays scannable. Loaded on demand.


## Common misconceptions (from Mindset)

Three misconceptions dominate Roles Anywhere misdesign at provisioning
time:

- **"The trust anchor alone grants access."** It does not. The trust
  anchor only binds your external CA to AWS IAM — it tells AWS "trust
  certificates signed by this CA." A profile is ALSO required to map
  the certificate to an IAM role, and the IAM role's trust policy must
  allow `sts:AssumeRole` from `rolesanywhere.amazonaws.com` (or use
  `sts:SetSourceIdentity` and the `AssumeRoot` action). Without all
  three (trust anchor + profile + IAM role with correct trust policy),
  the credential helper fails to obtain credentials.

- **"Any certificate from the CA can assume any role."** It cannot.
  The profile's `roleArns` list (or role-passthrough mode) determines
  which IAM roles the certificate can assume. Even if the certificate
  is valid and signed by a trusted CA, the profile must explicitly
  list the role ARN. An over-permissive profile violates least
  privilege; an under-permissive one results in `AccessDenied`.

- **"Revocation is automatic."** It is not. By default, a certificate
  remains valid until its expiration date. To revoke before expiration,
  you must configure a Certificate Revocation List (CRL). Without
  revocation, a compromised certificate remains usable until it
  expires. This is the #1 cause of "we revoked the cert in the CA but
  AWS still accepts it" incidents.


## Configuration dependency graph (sequencing notes)

Roles Anywhere configurations are NOT independent. The trust anchor
must bind the CA before the profile can map certificates; the IAM
role's trust policy must allow Roles Anywhere before assume works; the
credential helper must reference the correct profile and certificate
before the workload can authenticate. Use this graph to sequence
provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| External CA (PKI) | CA exists and can sign X.509 certificates | CA private key must be securely stored; CA cert must be in PEM format | trust anchor |
| Trust anchor | CA certificate in PEM format | trust anchor is immutable once created; to rotate the CA, create a new trust anchor and update the profile | AWS trusts certs from this CA |
| IAM role (trust policy) | role exists; trust policy allows `sts:AssumeRole` from `rolesanywhere.amazonaws.com` (or service principal for AssumeRoot) | without the trust policy, assume fails with `AccessDenied` — opaque to the client | role can be assumed via Roles Anywhere |
| IAM role (permissions) | role has permissions for the target AWS actions | over-permissive role violates least-privilege; under-permissive role causes API failures | temporary credentials have the right scope |
| Profile | trust anchor exists; roleArns reference valid IAM roles | role-passthrough mode lets the client specify the role ARN at assume time — use with caution | certificate-to-role mapping |
| Session policy | profile references a managed or inline session policy | session policy further restricts (never expands) the IAM role's permissions | scoped session |
| Credential helper | client certificate + private key + profile ID + trust anchor ID | helper signs requests with the certificate; without it, the client cannot authenticate | temporary credentials on the client |
| Revocation (CRL) | CRL endpoint reachable by Roles Anywhere; CRL signed by the CA | without revocation, compromised certs remain valid until expiration | compromised certs are rejected |
| CloudTrail audit | CloudTrail logging enabled in the account | AssumeRoot events are logged under the `AssumeRoot` event name in CloudTrail | compliance audit trail |

**The trust-policy-on-the-IAM-role row is the one a baseline model
misses.** A baseline says "create a trust anchor and profile." The
correct heuristic recognizes that the IAM role's trust policy must
explicitly allow `sts:AssumeRole` from `rolesanywhere.amazonaws.com`.
Without this trust policy, the credential helper returns
`AccessDenied` even with a valid certificate, trust anchor, and
profile.

**Cross-dependency gotchas:**
- A role that trusts only `ec2.amazonaws.com` (EC2 instance profile)
  CANNOT be assumed via Roles Anywhere — it must trust
  `rolesanywhere.amazonaws.com`.
- The profile's `roleArns` must match the IAM role ARN exactly. A
  mismatch (wrong path or wrong role name) causes assume to fail.
- The credential helper requires the certificate AND the private key —
  the helper signs the request with the private key to prove possession.
- Session policies RESTRICT permissions; they never expand them. A
  session policy cannot grant more than the IAM role's policies allow.
- Revocation (CRL) must be configured at the trust anchor level. A CRL
  applies to ALL certificates issued by the CA bound to that anchor.


## Expert heuristic: the three-legged trust stool

A baseline model says "create a trust anchor." The correct heuristic
recognizes that Roles Anywhere requires three components to function:

```text
Three-legged trust stool:
  1. Trust anchor (binds external CA to AWS IAM)
     → "AWS trusts certificates signed by this CA"
     → Without: AWS rejects all certificates from your PKI

  2. Profile (maps external certificate to IAM role)
     → "A certificate from this CA can assume these IAM roles"
     → Without: AWS does not know which role to assume

  3. IAM role (with trust policy for rolesanywhere.amazonaws.com)
     → "This role can be assumed by Roles Anywhere"
     → Without: assume fails with AccessDenied

All three must exist. Missing any one results in opaque failure — the
credential helper returns AccessDenied without indicating which is wrong.
```

**Key implication:** the #1 cause of "Roles Anywhere doesn't work" is a
missing or incorrect trust policy on the IAM role. Always verify the
role's trust policy includes `rolesanywhere.amazonaws.com` as a
principal.


## Expert heuristic: the credential helper signs requests with the certificate

The AWS signing helper (`aws_signing_helper`) is the client-side tool
that exchanges an X.509 certificate for STS temporary credentials,
signing the AssumeRole request with the certificate's private key to
prove possession.

```text
Credential helper workflow:
  1. Client has: certificate.pem, private-key.pem, profile-id, role-arn
  2. aws_signing_helper sign-request:
     → Reads the certificate and private key
     → Constructs an AssumeRole request
     → Signs the request with the private key
     → Sends to Roles Anywhere endpoint
  3. Roles Anywhere validates:
     → Certificate is signed by the trust anchor's CA
     → Certificate is not expired (and not revoked, if CRL is configured)
     → Profile maps the certificate to the requested role
     → IAM role's trust policy allows Roles Anywhere
  4. Roles Anywhere returns STS temporary credentials:
     → AccessKeyId, SecretAccessKey, SessionToken
     → Expiration (based on session duration)
  5. Client uses the temporary credentials to call AWS APIs
```

**Key implication:** the credential helper must run on the client
machine (the workload that needs AWS access). It is not an AWS service
— it is a binary you download from AWS and run locally. Without it,
the workload cannot sign requests with the certificate.


## Expert heuristic: session policies restrict, never expand

A session policy is an optional inline or managed policy attached to
the profile. It further restricts the IAM role's permissions for
sessions assumed via that profile. Effective permissions = IAM role
permissions intersected with the session policy. If the IAM role
allows `s3:*` and the session policy allows `s3:GetObject` only, the
effective permission is `s3:GetObject` only. If the IAM role allows
`s3:GetObject` and the session policy allows `s3:PutObject` only, the
effective permission is NOTHING (empty intersection).

**Key implication:** use session policies to scope down a shared IAM
role for different profiles. For example, a "ci-runner" role with
`s3:*` can have a profile with a session policy restricting it to
`s3:GetObject` on a specific bucket. The session policy cannot grant
more than the role allows.


## Recent AWS features (2023-2026)

- **Roles Anywhere General Availability (2023):** IAM Roles Anywhere
  reached GA, enabling certificate-based authentication to AWS APIs
  for workloads outside of AWS.
- **ACM PCA integration (2023-2024):** Trust anchors can reference
  AWS Private Certificate Authority (ACM PCA) directly, simplifying
  CA management for AWS-native PKIs.
- **Session policies (2023-2024):** Profiles support inline and
  managed session policies, enabling per-profile permission scoping
  on a shared IAM role.
- **Role-passthrough mode (2023-2024):** Profiles can use role-
  passthrough mode, where the client specifies the role ARN at assume
  time (instead of the profile pre-listing role ARNs).
- **CRL revocation (2023-2024):** Certificate Revocation Lists (CRLs)
  can be attached to trust anchors, enabling revocation of compromised
  certificates before expiration.
- **Credential helper updates (2024-2025):** The AWS signing helper
  added `credential-process` output format (compatible with the AWS
  CLI credential process), and improved error messages.
- **Instance-based attribution (2024-2025):** Roles Anywhere sessions
  now include instance-based attribution in CloudTrail, making it
  easier to identify which workload assumed which role.
- **Cross-account trust anchors (2024-2025):** Trust anchors can be
  shared across accounts via AWS Resource Access Manager (RAM),
