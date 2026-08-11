# FIPS Compliance & SDK Integration

## FIPS 140-2 Level 3
- CloudHSM provides FIPS 140-2 Level 3 validated HSMs
- All cryptographic operations executed within HSM hardware boundary
- Keys never leave HSM unencrypted

## PKCS#11 Library
- Standard C-based API for cryptographic operations
- Configure: `/opt/cloudhsm/lib/libcloudhsm_pkcs11.so`
- Set environment: `n3fips_password=` (user:password format)

## JCE Provider (Java)
- Java Cryptography Extension provider
- Configure: `-Djava.class.path=...:$JAVA_HOME/lib/security/`
- Provider name: `CloudHSM`

## Common Operations
- Key generation: AES, RSA, EC
- Signing: RSA-PSS, ECDSA
- Hashing: SHA-256, SHA-384
- Random: FIPS-approved DRBG

## SSL/TLS Offload
- Private key stored in HSM
- Nginx/Apache PKCS#11 integration
- Certificate on host, key in HSM

## HA Considerations
- All HSMs in cluster are synchronized
- Session failover is transparent
- Min 2 AZs recommended for HA
