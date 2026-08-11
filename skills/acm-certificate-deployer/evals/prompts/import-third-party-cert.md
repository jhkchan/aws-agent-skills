# Eval: import-third-party-cert

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — imported certificate with PEM cert + key + chain, manual renewal noted (NOT auto-renewed)

## Prompt

Import a third-party TLS certificate into ACM in us-east-1. I
have the PEM certificate at ./certs/certificate.pem, the private
key at ./certs/private-key.pem, and the chain at
./certs/chain.pem. The certificate is from DigiCert and covers
api.example.com. Account ID: 123456789012.
