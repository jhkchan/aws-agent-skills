# Baseline (without skill): missing-ad-prerequisite

The model does NOT flag the missing Active Directory:

1. Proceeds with file system creation without checking AD prerequisites
2. Does NOT identify that FSx for Windows requires either AWS Managed AD or self-managed AD
3. Does not mention AD Connector as a routing option
4. No validation of AD domain credentials and DNS configuration
5. Output would fail at deployment time with invalid configuration error
