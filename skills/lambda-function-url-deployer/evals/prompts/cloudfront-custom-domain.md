# Eval: cloudfront-custom-domain

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — CloudFront distribution in front of function URL, custom domain api.example.com, DefaultTTL=0, query string forwarding, NONE auth for CloudFront compatibility

## Prompt

Create a Lambda function URL for function
my-edge-handler (runtime nodejs20.x) in us-east-1. Use
NONE auth and BUFFERED invoke mode. I need a CloudFront
custom domain at api.example.com pointing to the function
URL. No caching (DefaultTTL=0). Forward query strings. CORS
allow origins https://api.example.com, methods GET POST PUT
DELETE. Tags: Environment=production, Service=edge-api.
