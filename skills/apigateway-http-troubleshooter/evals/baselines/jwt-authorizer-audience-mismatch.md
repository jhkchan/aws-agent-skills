# Baseline (no-skill) response: jwt-authorizer-audience-mismatch

---

Your API is returning 403 Forbidden. This means the JWT authorizer is
rejecting the request. Make sure your Cognito user pool is configured
correctly and that the token hasn't expired.

Check that the authorizer's issuer URL matches your Cognito user pool.
You might also want to verify that the token is being sent in the
Authorization header as a Bearer token. If the issuer matches, it could
be a problem with the audience configuration — double-check the
audience setting on the authorizer.
