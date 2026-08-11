# Baseline (no-skill) response: cors-preflight-headers-missing

---

You have a CORS error. This means your API Gateway is not returning
the right CORS headers. Make sure you've enabled CORS on your API and
that the AllowOrigins includes your frontend domain.

The error might be because your API Gateway is not handling OPTIONS
requests properly. Try adding CORS configuration in the API Gateway
console. You might also need to add an OPTIONS mock integration.
