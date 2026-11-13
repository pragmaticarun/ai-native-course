// Generates pages from repo files before every build:
//  - /syllabus/  from ../SYLLABUS.md
//  - /changelog/ from ../CHANGELOG.md
//  - /reference/versions/ from the lockfiles (what CI actually tested)
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..", "..");
const docs = resolve(import.meta.dirname, "..", "src", "content", "docs");
const read = (p) => readFileSync(resolve(root, p), "utf8");
const today = new Date().toISOString().slice(0, 10);

function page(title, description, body) {
  return `---\ntitle: ${JSON.stringify(title)}\ndescription: ${JSON.stringify(description)}\n---\n\n${body}\n`;
}

// Drop the first H1 (Starlight renders the title) and escape MDX-unsafe bits by keeping .md.
const stripH1 = (md) => md.replace(/^# .*\n+/, "");

writeFileSync(resolve(docs, "syllabus.md"), page(
  "Syllabus (v0.3)",
  "The full course syllabus and site outline, as approved.",
  `:::note\nGenerated from [SYLLABUS.md](https://github.com/pragmaticarun/ai-native-course/blob/main/SYLLABUS.md). Modules M0–M3 are built; the rest is the plan.\n:::\n\n${stripH1(read("SYLLABUS.md"))}`,
));

writeFileSync(resolve(docs, "changelog.md"), page(
  "Changelog", "Content, dependency and spec changes.", stripH1(read("CHANGELOG.md")),
));

// --- versions from lockfiles
const uvLock = read("python/uv.lock");
const py = {};
for (const m of uvLock.matchAll(/\[\[package\]\]\nname = "([^"]+)"\nversion = "([^"]+)"/g)) py[m[1]] = m[2];
const pyproject = read("python/pyproject.toml");
const direct = [...pyproject.matchAll(/"([A-Za-z0-9_.-]+)(?:\[[^\]]*\])?==([^"]+)"/g)].map((m) => m[1].toLowerCase());

function pnpmVersions(lockPath, pkgPath) {
  const lock = read(lockPath);
  const pkg = JSON.parse(read(pkgPath));
  const names = { ...pkg.dependencies, ...pkg.devDependencies };
  return Object.entries(names).map(([name, spec]) => {
    const re = new RegExp(`\\n\\s{6}'?${name.replace(/[/@.]/g, (c) => "\\" + c)}'?:\\n\\s+specifier: [^\\n]+\\n\\s+version: ([^\\s(]+)`);
    return [name, lock.match(re)?.[1] ?? `${spec} (not in lockfile)`];
  });
}
const rows = (pairs) => pairs.map(([n, v]) => `| \`${n}\` | ${v} |`).join("\n");

const body = `Generated at build time (${today}) from the lockfiles, so this always matches what CI tested.

## Runtimes
| Tool | Version |
|---|---|
| Python | ${read("python/.python-version").trim()} (CI also runs 3.14) |
| Node.js | 24 LTS |
| pnpm | ${JSON.parse(read("package.json")).packageManager.split("@")[1]} |

## Python (\`python/uv.lock\`, direct dependencies)
| Package | Locked version |
|---|---|
${rows(direct.filter((n) => py[n]).map((n) => [n, py[n]]))}

## TypeScript examples (\`pnpm-lock.yaml\`)
| Package | Locked version |
|---|---|
${rows(pnpmVersions("pnpm-lock.yaml", "package.json"))}

## Site (\`site/pnpm-lock.yaml\`)
| Package | Locked version |
|---|---|
${rows(pnpmVersions("site/pnpm-lock.yaml", "site/package.json"))}

Versions for later modules (LangGraph, MCP SDKs, Temporal, Android/KMP, media and on-device runtimes) are planned in the [syllabus](/ai-native-course/syllabus/) section 2.4 and will appear here when their lessons ship.
`;
writeFileSync(resolve(docs, "reference", "versions.md"), page("Versions", "Pinned versions, generated from the lockfiles.", body));
console.log("generated syllabus.md, changelog.md, reference/versions.md");
