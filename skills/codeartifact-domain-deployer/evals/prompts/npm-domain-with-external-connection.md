# Eval: npm-domain-with-external-connection

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — npm domain, internal upstream first, external connection to npmjs.com last, 12-hour auth token expiry noted

## Prompt

Create a CodeArtifact domain called my-domain in us-east-1,
account 123456789012. Create an npm repository my-team-packages
within it. Add an upstream to shared-team-packages (internal)
and an external connection to npmjs.com. The cascade order must
put the internal repo before the public registry. Tags:
Environment=production, Team=platform.
