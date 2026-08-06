#!/usr/bin/env node
// AWS CloudOps Agent Skills — CLI entry point
// Mirrors the reference repo's cli/bin/cli.js but is FUNCTIONAL (not a stub).
// Commands: list, route <prompt>, validate, status, help
//
// Usage:
//   node cli/bin/cli.js list
//   node cli/bin/cli.js route "check my S3 buckets for public access"
//   node cli/bin/cli.js validate
//   node cli/bin/cli.js status
//   node cli/bin/cli.js help

import { readFileSync, readdirSync, existsSync } from "fs";
import { join, dirname, resolve } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const REPO_ROOT = resolve(__dirname, "..", "..");
const SKILLS_DIR = join(REPO_ROOT, "skills");

// ---------------------------------------------------------------------------
// Skill discovery — scans skills/*/SKILL.md, parses YAML frontmatter
// ---------------------------------------------------------------------------

function parseFrontmatter(text) {
  if (!text.startsWith("---")) return {};
  const parts = text.split("---", 3);
  if (parts.length < 3) return {};
  const yamlBlock = parts[1];
  const fm = {};
  let currentKey = null;
  let inList = false;

  for (const line of yamlBlock.split("\n")) {
    const trimmed = line.trimEnd();
    if (!trimmed.trim()) continue;

    // List item under a key (  - value)
    const listMatch = trimmed.match(/^\s+-\s+(.+)$/);
    if (listMatch && currentKey) {
      if (!Array.isArray(fm[currentKey])) fm[currentKey] = [];
      fm[currentKey].push(listMatch[1].replace(/^["']|["']$/g, ""));
      inList = true;
      continue;
    }

    // Key: value
    const kvMatch = trimmed.match(/^(\w[\w_]*)\s*:\s*(.*)$/);
    if (kvMatch) {
      const [, key, value] = kvMatch;
      currentKey = key;
      inList = false;
      if (value.trim()) {
        // Inline value — strip quotes, handle YAML block scalars
        let v = value.trim();
        if (v === ">-" || v === ">" || v === "|-" || v === "|") {
          // Block scalar — collect subsequent indented lines
          fm[key] = "__BLOCK__";
        } else if (v.startsWith("[") && v.endsWith("]")) {
          // Inline YAML array: [a, b, c] -> ["a", "b", "c"]
          fm[key] = v
            .slice(1, -1)
            .split(",")
            .map((s) => s.trim().replace(/^["']|["']$/g, ""))
            .filter((s) => s.length > 0);
        } else {
          v = v.replace(/^["']|["']$/g, "");
          fm[key] = v;
        }
      } else {
        fm[key] = null;
      }
    } else if (currentKey && fm[currentKey] === "__BLOCK__" && trimmed.startsWith(" ")) {
      // Continuation of block scalar
      fm[currentKey] = (fm[currentKey] === "__BLOCK__" ? "" : fm[currentKey] + " ") + trimmed.trim();
    }
  }
  return fm;
}

function extractKeywords(text) {
  // Extract activation keywords from the SKILL.md body
  const keywordSection = text.match(/##\s+Activation keywords\s*\n([\s\S]*?)(?=\n##\s|$)/);
  if (keywordSection) {
    return keywordSection[1]
      .replace(/\n/g, " ")
      .split(/[,.]/)
      .map((s) => s.trim().toLowerCase())
      .filter((s) => s.length > 2 && !s.includes(":"));
  }
  return [];
}

function discoverSkills() {
  if (!existsSync(SKILLS_DIR)) return [];
  const skills = [];
  for (const entry of readdirSync(SKILLS_DIR, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    if (entry.name.startsWith("_") || entry.name.startsWith(".")) continue;
    const skillMdPath = join(SKILLS_DIR, entry.name, "SKILL.md");
    if (!existsSync(skillMdPath)) continue;

    const raw = readFileSync(skillMdPath, "utf-8");
    const frontmatter = parseFrontmatter(raw);
    const keywords = extractKeywords(raw);

    const hasEval = existsSync(join(SKILLS_DIR, entry.name, "eval"));
    const hasEvals = existsSync(join(SKILLS_DIR, entry.name, "evals"));
    const hasReferences = existsSync(join(SKILLS_DIR, entry.name, "references"));

    skills.push({
      name: frontmatter.name || entry.name,
      description: frontmatter.description || "",
      version: frontmatter.version || "unknown",
      keywords: [...(frontmatter.keywords || []), ...keywords],
      tags: frontmatter.tags || [],
      dependencies: frontmatter.dependencies || [],
      metadata: frontmatter.metadata || {},
      dir: entry.name,
      hasEval,
      hasEvals,
      hasReferences,
    });
  }
  return skills;
}

// ---------------------------------------------------------------------------
// Routing — keyword + description match scoring (functional orchestrator)
// ---------------------------------------------------------------------------

function route(prompt, skills) {
  const promptLower = prompt.toLowerCase();
  const promptTokens = promptLower.split(/\s+/).filter((t) => t.length > 2);

  const scored = skills
    .filter((s) => !s.name.endsWith("-orchestrator") || skills.length === 1)
    .map((skill) => {
      let score = 0;
      const descLower = (skill.description || "").toLowerCase();
      const allKeywords = [...skill.keywords, ...(skill.tags || [])].map((k) =>
        k.toLowerCase()
      );

      // Exact keyword matches (high weight)
      for (const kw of allKeywords) {
        if (promptLower.includes(kw)) {
          score += kw.length > 6 ? 5 : 3;
        }
      }

      // Token overlap with description
      for (const token of promptTokens) {
        if (descLower.includes(token)) score += 2;
      }

      // Skill name token overlap
      const nameTokens = skill.name.split("-");
      for (const nToken of nameTokens) {
        if (promptLower.includes(nToken) && nToken.length > 2) score += 4;
      }

      // Phase match: if the prompt mentions "audit"/"check"/"review" and skill is phase 2 (Audit)
      const auditVerbs = ["audit", "check", "review", "scan", "inspect", "assess"];
      if (auditVerbs.some((v) => promptLower.includes(v))) {
        score += 1;
      }

      return { skill: skill.name, score, dir: skill.dir };
    })
    .filter((s) => s.score > 0)
    .sort((a, b) => b.score - a.score);

  return scored;
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

function cmdList() {
  const skills = discoverSkills();
  if (skills.length === 0) {
    console.log("No skills found in skills/");
    return;
  }
  console.log(`\nAWS CloudOps Agent Skills (${skills.length}):\n`);
  for (const s of skills) {
    const evalBadge = s.hasEval || s.hasEvals ? "eval-backed" : "NO EVAL";
    const refBadge = s.hasReferences ? "refs" : "no-refs";
    console.log(`  ${s.name.padEnd(40)} v${s.version}  [${evalBadge}] [${refBadge}]`);
    if (s.description) {
      const desc = s.description.length > 100
        ? s.description.substring(0, 97) + "..."
        : s.description;
      console.log(`    ${desc}\n`);
    }
  }
}

function cmdRoute(prompt) {
  if (!prompt) {
    console.error('Usage: aws-skills route "your prompt here"');
    process.exit(1);
  }
  const skills = discoverSkills();
  const results = route(prompt, skills);

  if (results.length === 0) {
    console.log("No matching skills found. Try /aws:help for available skills.");
    return;
  }

  const top = results[0];
  const others = results.slice(1, 4);

  // Emit phase indicator (mirrors the orchestrator skill format)
  const phase = inferPhase(prompt);
  console.log(
    `[Phase: ${phase} | Skills routed: ${results.slice(0, 3).map((r) => r.skill).join(", ")}]`
  );
  console.log(`\nPrimary route: ${top.skill} (score: ${top.score})`);

  // Read and display the skill's description
  const skill = skills.find((s) => s.name === top.skill);
  if (skill) {
    console.log(`\n${skill.description}\n`);
  }

  if (others.length > 0) {
    console.log("Also relevant:");
    for (const o of others) {
      console.log(`  - ${o.skill} (score: ${o.score})`);
    }
  }
}

function inferPhase(prompt) {
  const lower = prompt.toLowerCase();
  if (/remediate|fix|patch|remediation|repair|resolve/.test(lower)) return "Remediate";
  if (/prioriti|rank|severity|critical|order|importance/.test(lower)) return "Prioritize";
  if (/audit|check|review|scan|inspect|verdict|public|exposed|open|compliance/.test(lower))
    return "Audit";
  if (/inventory|enumerate|list|baseline|coverage|gap|discover/.test(lower)) return "Assess";
  return "Audit"; // default
}

function cmdValidate() {
  const skills = discoverSkills();
  let errors = 0;
  let warnings = 0;

  console.log("\nValidating skills against schema/SKILL.schema.json...\n");

  for (const s of skills) {
    const issues = [];
    if (!s.name) issues.push("ERROR: missing 'name'");
    if (!s.description || s.description.length < 10)
      issues.push("ERROR: 'description' must be >= 10 chars");
    if (s.description && s.description.length > 1024)
      issues.push("ERROR: 'description' must be <= 1024 chars");
    if (!s.version || s.version === "unknown")
      issues.push("WARN: missing 'version'");
    if (!s.hasEval && !s.hasEvals)
      issues.push("WARN: no eval/ or evals/ directory");

    if (issues.length === 0) {
      console.log(`  ${s.name}: OK`);
    } else {
      for (const issue of issues) {
        console.log(`  ${s.name}: ${issue}`);
        if (issue.startsWith("ERROR")) errors++;
        else warnings++;
      }
    }
  }

  console.log(`\n${errors} errors, ${warnings} warnings`);
  process.exit(errors > 0 ? 1 : 0);
}

function cmdStatus() {
  const skills = discoverSkills();
  const audited = skills.filter((s) => s.hasEval || s.hasEvals);
  const orchestrator = skills.find((s) => s.name === "aws-orchestrator");

  console.log("\nAWS CloudOps Skills — Status");
  console.log("=".repeat(50));
  console.log(`Total skills:        ${skills.length}`);
  console.log(`Eval-backed:         ${audited.length}`);
  console.log(`Orchestrator:        ${orchestrator ? "present" : "MISSING"}`);
  console.log(
    `Pipeline phases:     Assess -> Audit -> Prioritize -> Remediate`
  );

  // Per-skill eval status
  console.log("\nPer-skill eval status:");
  for (const s of skills) {
    const status = s.hasEval || s.hasEvals ? "[eval-backed]" : "[NO EVAL     ]";
    console.log(`  ${status}  ${s.name}`);
  }
}

function cmdHelp() {
  console.log(`
AWS CloudOps Agent Skills CLI

Usage:
  aws-skills <command> [args]

Commands:
  list              List all discovered skills with eval status
  route <prompt>    Route a natural-language prompt to the best-matching skill(s)
  validate          Validate all skills against schema/SKILL.schema.json
  status            Show skill-suite coverage + eval status summary
  help              Show this help message

Slash commands (in Claude Code / Cursor / Windsurf):
  /aws:pipeline     Enter the full CloudOps pipeline (Assess -> Audit -> Prioritize -> Remediate)
  /aws:status       One-line phase + skill-routing summary
  /aws:help         List all commands + natural-language triggers

Pipeline phases:
  1. Assess      — inventory resources, enumerate coverage gaps, baseline state
  2. Audit       — detective auditors: read AWS config, emit deterministic VERDICT
  3. Prioritize  — rank findings by severity, cost-impact, compliance-mandate
  4. Remediate   — generate remediation CLI commands, IaC patches, runbook steps
`);
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

const [command, ...args] = process.argv.slice(2);

switch (command) {
  case "list":
    cmdList();
    break;
  case "route":
    cmdRoute(args.join(" "));
    break;
  case "validate":
    cmdValidate();
    break;
  case "status":
    cmdStatus();
    break;
  case "help":
  case "--help":
  case "-h":
  case undefined:
    cmdHelp();
    break;
  default:
    console.error(`Unknown command: ${command}`);
    cmdHelp();
    process.exit(1);
}
