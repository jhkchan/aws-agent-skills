#!/usr/bin/env node
// AWS CloudOps Agent Skills — CLI entry point
// A functional CLI for skill discovery, routing, and validation.
// Commands: list, route <prompt>, validate, status, impact, help
//
// Usage:
//   node cli/bin/cli.js list
//   node cli/bin/cli.js list --task-type deploy
//   node cli/bin/cli.js route "check my S3 buckets for public access"
//   node cli/bin/cli.js route "deploy a secure VPC"
//   node cli/bin/cli.js validate
//   node cli/bin/cli.js status
//   node cli/bin/cli.js impact
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
  // One level of nesting (agentskills.io metadata map): `metadata:` with
  // indented `  key: value` children. Lists and block scalars supported at
  // both levels.
  let currentKey = null;
  let currentMap = fm; // fm itself, or fm.metadata while inside the nested map
  let inMetadata = false;

  const setKey = (map, key, value) => {
    map[key] = value;
  };

  for (const line of yamlBlock.split("\n")) {
    const trimmed = line.trimEnd();
    if (!trimmed.trim()) continue;

    // List item under a key (any indent)
    const listMatch = trimmed.match(/^\s+-\s+(.+)$/);
    if (listMatch && currentKey) {
      if (!Array.isArray(currentMap[currentKey])) currentMap[currentKey] = [];
      currentMap[currentKey].push(listMatch[1].replace(/^["']|["']$/g, ""));
      continue;
    }

    // Indented key: value — nested map member (metadata)
    const nestedMatch = trimmed.match(/^[ ]{2,}([\w][\w_-]*)\s*:\s*(.*)$/);
    if (nestedMatch && inMetadata && currentMap !== fm) {
      const [, key, value] = nestedMatch;
      currentKey = key;
      if (value.trim()) {
        let v = value.trim();
        if (v === ">-" || v === ">" || v === "|-" || v === "|") {
          setKey(currentMap, key, "__BLOCK__");
        } else if (v.startsWith("[") && v.endsWith("]")) {
          setKey(
            currentMap,
            key,
            v
              .slice(1, -1)
              .split(",")
              .map((s) => s.trim().replace(/^["']|["']$/g, ""))
              .filter((s) => s.length > 0)
          );
        } else {
          setKey(currentMap, key, v.replace(/^["']|["']$/g, ""));
        }
      } else {
        setKey(currentMap, key, null);
      }
      continue;
    }

    // Top-level key: value
    const kvMatch = trimmed.match(/^(\w[\w_]*)\s*:\s*(.*)$/);
    if (kvMatch) {
      const [, key, value] = kvMatch;
      currentKey = key;
      inMetadata = false;
      currentMap = fm;
      if (value.trim()) {
        let v = value.trim();
        if (v === ">-" || v === ">" || v === "|-" || v === "|") {
          setKey(fm, key, "__BLOCK__");
        } else if (v.startsWith("[") && v.endsWith("]")) {
          setKey(
            fm,
            key,
            v
              .slice(1, -1)
              .split(",")
              .map((s) => s.trim().replace(/^["']|["']$/g, ""))
              .filter((s) => s.length > 0)
          );
        } else {
          setKey(fm, key, v.replace(/^["']|["']$/g, ""));
        }
      } else {
        if (key === "metadata") {
          // Enter nested map
          setKey(fm, "metadata", {});
          inMetadata = true;
          currentMap = fm.metadata;
        } else {
          setKey(fm, key, null);
        }
      }
    } else if (currentKey && currentMap[currentKey] === "__BLOCK__" && trimmed.startsWith(" ")) {
      // Continuation of block scalar
      currentMap[currentKey] =
        (currentMap[currentKey] === "__BLOCK__" ? "" : currentMap[currentKey] + " ") + trimmed.trim();
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

    // Extract task_type from metadata (default: audit for backward compat)
    const meta = frontmatter.metadata || {};
    const taskType = meta.task_type || inferTaskTypeFromName(entry.name);

    // Spec (agentskills.io) frontmatter: version/keywords/tags/dependencies live
    // in metadata as comma-joined strings. Legacy top-level arrays also accepted.
    const splitCsv = (v) =>
      typeof v === "string" ? v.split(",").map((s) => s.trim()).filter(Boolean) : Array.isArray(v) ? v : [];

    skills.push({
      name: frontmatter.name || entry.name,
      description: frontmatter.description || "",
      version: meta.version || frontmatter.version || "unknown",
      keywords: [...splitCsv(meta.keywords ?? frontmatter.keywords), ...keywords],
      tags: splitCsv(meta.tags ?? frontmatter.tags),
      dependencies: splitCsv(meta.dependencies ?? frontmatter.dependencies),
      metadata: meta,
      taskType,
      skillClass: meta.skill_class || (taskType === "audit" ? "capability" : "capability"),
      lifecycleStatus: meta.lifecycle_status || "active",
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

// Infer task_type from skill name suffix when metadata is absent (backward compat)
function inferTaskTypeFromName(name) {
  if (/auditor$|advisor$|triage$|inventory$/.test(name)) return "audit";
  if (/deployer$/.test(name)) return "deploy";
  if (/troubleshooter$/.test(name)) return "troubleshoot";
  if (/optimizer$/.test(name)) return "optimize";
  if (/operator$/.test(name)) return "operate";
  if (/automator$/.test(name)) return "automate";
  return "audit";
}

// Task-type keyword map for routing
const TASK_TYPE_KEYWORDS = {
  audit: ["audit", "check", "review", "scan", "inspect", "assess", "compliance", "posture", "verdict", "exposed", "vulnerable"],
  deploy: ["deploy", "provision", "create", "set up", "build", "configure", "infrastructure", "terraform", "cdk", "cloudformation", "provision"],
  troubleshoot: ["troubleshoot", "debug", "diagnose", "error", "fail", "failing", "broken", "why is", "cannot", "unable", "access denied", "connection refused", "timeout"],
  optimize: ["optimize", "reduce cost", "save money", "cheaper", "right-size", "rightsizing", "performance", "faster", "efficient", "lifecycle", "reserved", "savings plan"],
  operate: ["backup", "restore", "snapshot", "rotate", "patch", "scale", "failover", "upgrade", "renew", "day-2", "operate", "maintenance"],
  automate: ["automate", "pipeline", "ci/cd", "continuous", "event-driven", "schedule", "workflow", "runbook", "automation", "remediation"],
};

function inferTaskType(prompt) {
  const lower = prompt.toLowerCase();
  let bestType = "audit";
  let bestScore = 0;
  for (const [type, keywords] of Object.entries(TASK_TYPE_KEYWORDS)) {
    const score = keywords.filter((kw) => lower.includes(kw)).length;
    if (score > bestScore) {
      bestScore = score;
      bestType = type;
    }
  }
  return bestType;
}

function route(prompt, skills) {
  const promptLower = prompt.toLowerCase();
  const promptTokens = promptLower.split(/\s+/).filter((t) => t.length > 2);
  const detectedTaskType = inferTaskType(prompt);

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

      // Task-type match: boost skills whose task_type matches the detected intent
      // and penalize mismatches (a deploy skill shouldn't win for an audit prompt)
      if (skill.taskType === detectedTaskType) {
        score += 5;
      } else if (skill.taskType && skill.taskType !== "audit") {
        // Non-audit skill for a non-matching task type: mild penalty
        score -= 3;
      }

      return { skill: skill.name, score, dir: skill.dir, taskType: skill.taskType };
    })
    .filter((s) => s.score > 0)
    .sort((a, b) => b.score - a.score);

  return scored;
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

function cmdList(filterTaskType) {
  let skills = discoverSkills();
  if (skills.length === 0) {
    console.log("No skills found in skills/");
    return;
  }
  if (filterTaskType) {
    skills = skills.filter((s) => s.taskType === filterTaskType);
    console.log(`\nAWS CloudOps Agent Skills — task_type=${filterTaskType} (${skills.length}):\n`);
  } else {
    console.log(`\nAWS CloudOps Agent Skills (${skills.length}):\n`);
  }

  // Group by task type
  const byType = {};
  for (const s of skills) {
    const tt = s.taskType || "audit";
    if (!byType[tt]) byType[tt] = [];
    byType[tt].push(s);
  }

  for (const tt of Object.keys(byType).sort()) {
    if (!filterTaskType) console.log(`--- ${tt} (${byType[tt].length}) ---`);
    for (const s of byType[tt]) {
      const evalBadge = s.hasEval || s.hasEvals ? "eval-backed" : "NO EVAL";
      const refBadge = s.hasReferences ? "refs" : "no-refs";
      const classBadge = s.skillClass ? `[${s.skillClass}]` : "";
      console.log(`  ${s.name.padEnd(45)} v${s.version}  [${evalBadge}] [${refBadge}] ${classBadge}`);
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

  // Emit task-type indicator (replaces phase-only inference)
  const taskType = inferTaskType(prompt);
  console.log(
    `[Task: ${taskType} | Skills routed: ${results.slice(0, 3).map((r) => r.skill).join(", ")}]`
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

// Legacy phase inference (for backward compat with orchestrator)
function inferPhase(prompt) {
  const taskType = inferTaskType(prompt);
  const phaseMap = {
    audit: "Audit",
    deploy: "Remediate",
    troubleshoot: "Audit",
    optimize: "Prioritize",
    operate: "Remediate",
    automate: "Remediate",
  };
  return phaseMap[taskType] || "Audit";
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
  const evalBacked = skills.filter((s) => s.hasEval || s.hasEvals);
  const orchestrator = skills.find((s) => s.name === "aws-orchestrator");

  // Task-type breakdown
  const byType = {};
  for (const s of skills) {
    const tt = s.taskType || "audit";
    if (!byType[tt]) byType[tt] = { total: 0, evalBacked: 0 };
    byType[tt].total++;
    if (s.hasEval || s.hasEvals) byType[tt].evalBacked++;
  }

  console.log("\nAWS CloudOps Skills — Status");
  console.log("=".repeat(60));
  console.log(`Total skills:        ${skills.length}`);
  console.log(`Eval-backed:         ${evalBacked.length}`);
  console.log(`Orchestrator:        ${orchestrator ? "present" : "MISSING"}`);
  console.log("");
  console.log("By task type:");
  for (const tt of Object.keys(byType).sort()) {
    const d = byType[tt];
    console.log(`  ${tt.padEnd(15)} ${String(d.total).padStart(4)} skills  (${d.evalBacked} eval-backed)`);
  }
  console.log("");
  console.log("Task types:  audit -> deploy -> troubleshoot -> optimize -> operate -> automate");
}

function cmdHelp() {
  console.log(`
AWS CloudOps Agent Skills CLI

Usage:
  aws-skills <command> [args]

Commands:
  list [--task-type <type>]  List skills, optionally filtered by task type
  route <prompt>             Route a natural-language prompt to best skill(s)
  validate                   Validate all skills against schema/SKILL.schema.json
  status                     Show skill-suite coverage + eval status summary
  impact                     Show impact-eval recommendations (retirement cadence)
  help                       Show this help message

Task types:
  audit        Assess security posture, compliance, configuration drift
  deploy       Provision infrastructure with correct defaults and best practices
  troubleshoot Diagnose and resolve operational issues (errors, slowness, downtime)
  optimize     Reduce cost or improve performance (right-sizing, lifecycle, caching)
  operate      Day-2 operations (backup, restore, scale, patch, rotate, failover)
  automate     Workflow/pipeline patterns (CI/CD, event-driven, auto-remediation, IaC)

Slash commands (in Claude Code / Cursor / Windsurf):
  /aws:pipeline     Enter the full CloudOps pipeline
  /aws:status       One-line task-type + skill-routing summary
  /aws:help         List all commands + natural-language triggers
`);
}

function cmdImpact() {
  const impactDir = join(REPO_ROOT, "eval", "impact-reports");
  if (!existsSync(impactDir)) {
    console.log("\nNo impact reports found.");
    console.log("Run: python3 eval/impact_eval.py [--skill <name>]");
    return;
  }

  const reports = [];
  for (const entry of readdirSync(impactDir)) {
    if (!entry.endsWith(".json")) continue;
    try {
      const data = JSON.parse(readFileSync(join(impactDir, entry), "utf-8"));
      reports.push(data);
    } catch (e) {
      // skip malformed
    }
  }

  if (reports.length === 0) {
    console.log("\nNo impact reports found.");
    console.log("Run: python3 eval/impact_eval.py [--skill <name>]");
    return;
  }

  reports.sort((a, b) => (b.avg_delta || 0) - (a.avg_delta || 0));

  console.log("\nImpact Evaluation Reports");
  console.log("=".repeat(70));
  console.log(`${"Skill".padEnd(45)} ${"Avg Δ".padStart(6)}  ${"Cases".padStart(5)}  Recommendation`);
  console.log("-".repeat(70));
  for (const r of reports) {
    const delta = r.avg_delta !== undefined ? (r.avg_delta > 0 ? "+" : "") + r.avg_delta.toFixed(1) : "N/A";
    console.log(
      `${(r.skill || "?").padEnd(45)} ${delta.padStart(6)}  ${String(r.case_count || 0).padStart(5)}  ${r.recommendation || "UNKNOWN"}`
    );
  }
  console.log("-".repeat(70));

  const retire = reports.filter((r) => r.recommendation === "RETIRE_CANDIDATE");
  const low = reports.filter((r) => r.recommendation === "LOW_IMPACT");
  if (retire.length > 0) {
    console.log(`\n⚠ RETIRE CANDIDATES (${retire.length}):`);
    for (const r of retire) {
      console.log(`  - ${r.skill} (avg delta: ${r.avg_delta})`);
    }
  }
  if (low.length > 0) {
    console.log(`\n⚠ LOW IMPACT (${low.length}):`);
    for (const r of low) {
      console.log(`  - ${r.skill} (avg delta: ${r.avg_delta})`);
    }
  }
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

const [command, ...args] = process.argv.slice(2);

switch (command) {
  case "list": {
    const ttIdx = args.indexOf("--task-type");
    const filterTaskType = ttIdx >= 0 ? args[ttIdx + 1] : undefined;
    cmdList(filterTaskType);
    break;
  }
  case "route":
    cmdRoute(args.join(" "));
    break;
  case "validate":
    cmdValidate();
    break;
  case "status":
    cmdStatus();
    break;
  case "impact":
    cmdImpact();
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
