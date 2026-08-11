# Eval: public-dns-cloudfront

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — public cert, DNS validation, us-east-1 (CloudFront requirement), apex + wildcard domains, CloudFront integration

## Prompt

Request a public ACM certificate for example.com and
*.example.com with DNS validation in us-east-1. Attach it to
CloudFront distribution E1234567890ABC. Route53 hosted zone
Z2KVMGOMGDOOU2. Key algorithm RSA_2048. Tags:
Environment=production, Service=website. Account ID:
123456789012.
