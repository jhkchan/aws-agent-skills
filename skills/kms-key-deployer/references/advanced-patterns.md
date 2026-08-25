# Advanced Patterns — kms-key-deployer

Recent AWS feature notes moved verbatim from SKILL.md.

## Recent AWS features (2024-2026) — detail

- **On-demand key rotation (2024-2025):** `kms:RotateKeyOnDemand`
  triggers immediate rotation for eligible symmetric CMKs, bypassing
  the annual schedule. Use for incident response (suspected key
  compromise). The key ARN and policy do not change.

- **Key spec HMAC_256 GA (2024):** HMAC keys for message authentication
  (JWT signing, API tokens). `KeyUsage=GENERATE_VERIFY_MAC`. Does NOT
  support automatic rotation.

- **CloudHSM custom key store rotation (2024-2025):** custom key store
  keys now support automatic rotation in more Regions.

- **ECDH key agreement (2024-2025):** `ECC_NIST_P256`/`P384` with
  `KeyUsage=KEY_AGREEMENT` for mTLS and hybrid post-quantum schemes.

- **Key policy hash check (2024):** `DescribeKey` returns a hash of
  the key policy, enabling drift detection in CI.

- **XKS (External Key Store) GA (2024-2025):** for workloads needing
  key material outside AWS entirely (external HSM over a standard API).

- **VPC endpoint policy support (2024):** KMS interface VPC endpoints
  now support endpoint policies — control which CMKs are reachable.

- **MAC algorithms expanded (2025):** HMAC keys support additional MAC
  algorithm options via KeySpec.

