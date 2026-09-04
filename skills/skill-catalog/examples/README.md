# Example: precise skill selection

1. User: "my Lambda keeps timing out"
2. Agent loads this catalog, matches task_type=troubleshoot, family=Compute
3. Family listing → `lambda-timeout-troubleshooter`
4. Precise call: `@skills:gh:jhkchan/aws-agent-skills/skills/lambda-timeout-troubleshooter`
5. Skill body's diagnostic tree runs; SKILL.md loads only at this step (progressive disclosure)
