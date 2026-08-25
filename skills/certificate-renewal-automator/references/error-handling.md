# certificate-renewal-automator — error handling (moved from SKILL.md)

Progressive-disclosure reference. Content below was moved verbatim from SKILL.md; the agent loads it only when needed.

## Common DNS validation failures (Step 5)

| Failure | Fix |
|---|---|
| Validation never completes | Verify CNAME via `dig _abc.example.com CNAME` |
| Renewal fails later | CNAME was deleted — it must persist for the cert's lifetime |
| One SAN domain fails | Add CNAME for each SAN entry |
| CNAME conflict | Remove conflicting TXT/CNAME; ACM needs exclusive use |
