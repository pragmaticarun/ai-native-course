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
  `:::note\nGenerated from [SYLLABUS.md](https://github.com/pragmaticarun/ai-native-course/blob/main/SYLLABUS.md). Modules M0–M9 are built; the rest is the plan.\n:::\n\n${stripH1(read("SYLLABUS.md"))}`,
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
// Kotlin Multiplatform: version catalog + Gradle wrapper
const catalog = read("kmp/gradle/libs.versions.toml");
const versionsBlock = catalog.split("[versions]")[1].split("[")[0];
const kt = [...versionsBlock.matchAll(/^([A-Za-z0-9-]+)\s*=\s*"([^"]+)"/gm)].map((m) => [m[1], m[2]]);
const gradle = read("kmp/gradle/wrapper/gradle-wrapper.properties").match(/gradle-([0-9.]+)-bin\.zip/)?.[1] ?? "?";
// Rust: direct dependencies from Cargo.toml, resolved versions from Cargo.lock
const cargoToml = read("rust/media-probe/Cargo.toml");
const cargoLock = read("rust/media-probe/Cargo.lock");
const rustChannel = read("rust/media-probe/rust-toolchain.toml").match(/channel = "([^"]+)"/)?.[1] ?? "?";
const lockVersion = (name) => cargoLock.match(new RegExp(`\\[\\[package\\]\\]\\nname = "${name}"\\nversion = "([^"]+)"`))?.[1] ?? "?";
const rustDeps = [...new Set([...cargoToml.matchAll(/^([a-z0-9_-]+)\s*=/gm)].map((m) => m[1]))]
  .filter((n) => !["name", "version", "edition", "description", "license", "publish"].includes(n))
  .map((n) => [n, lockVersion(n)]);
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

## Kotlin Multiplatform (\`kmp/gradle/libs.versions.toml\`)
| Entry | Version |
|---|---|
${rows(kt)}
| Gradle (wrapper) | ${gradle} |
| JDK | 21 (Temurin in CI; \`jvmToolchain(21)\`) |

Only the JVM target is built and tested so far. Android-only entries (AGP, LiteRT-LM, ML Kit, ...) are added when the Android target lands.

## Rust (\`rust/media-probe/Cargo.lock\`)
| Crate | Locked version |
|---|---|
| Rust toolchain (\`rust-toolchain.toml\`) | ${rustChannel} |
${rows(rustDeps)}

## Site (\`site/pnpm-lock.yaml\`)
| Package | Locked version |
|---|---|
${rows(pnpmVersions("site/pnpm-lock.yaml", "site/package.json"))}

Versions for later modules (the Android target, media and on-device runtimes) are planned in the [syllabus](/ai-native-course/syllabus/) section 2.4 and will appear here when their lessons ship. The Temporal test/dev server binaries are downloaded by the Temporal SDKs at test time and are not pinned here.
`;
writeFileSync(resolve(docs, "reference", "versions.md"), page("Versions", "Pinned versions, generated from the lockfiles.", body));
console.log("generated syllabus.md, changelog.md, reference/versions.md");
