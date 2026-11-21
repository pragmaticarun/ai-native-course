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
  `:::note\nGenerated from [SYLLABUS.md](https://github.com/pragmaticarun/ai-native-course/blob/main/SYLLABUS.md). Modules M0–M15 are built (M13 up to the host side; its Android parts are untested); the projects are the plan.\n:::\n\n${stripH1(read("SYLLABUS.md"))}`,
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

Both KMP targets are built and tested in CI. The JVM target runs in the \`kmp\` job. Since 14 Nov 2026 (Android SDK install approved by the owner) the \`android\` job builds the Android target and P6's app: the Android host tests, \`assembleDebug\` and \`testDebugUnitTest\`. It also compiles the instrumentation APK, which is not run. AGP, Compose, Koog's LiteRT executor and LiteRT-LM above are what that build uses. **Untested:** nothing has run on a device, an emulator or the Galaxy A73 yet.

## Rust (\`rust/media-probe/Cargo.lock\`)
| Crate | Locked version |
|---|---|
| Rust toolchain (\`rust-toolchain.toml\`) | ${rustChannel} |
${rows(rustDeps)}

## Tools run by the tests (not lockfile-managed)
| Tool | Version | Where |
|---|---|---|
| GitHub Spec Kit (\`specify\`) | v1.4.0 (git tag) | M10; CI \`speckit\` job runs \`uvx --from git+https://github.com/github/spec-kit.git@v1.4.0 specify init\` |
| git | runner's version | M10 hooks, M11 worktrees and sandbox repos |
| llama.cpp | build b12428 (post-v1.0.0; prebuilt \`llama-b12428-bin-ubuntu-x64.tar.gz\`; checked 17 Nov 2026) | M13 quantization; CI \`llamacpp\` job with \`stories15M.gguf\` from \`ggml-org/models\` |
| browser-use | 1.0.6 (PyPI; isolated env, not in \`uv.lock\`, because its exact pins conflict with the course lock; checked 17 Nov 2026) | M15 API check, \`examples/python/m15/test_browser_use_pins.py\`; no agent run |
| Playwright browsers | Chromium bundled with \`playwright\` (Python, locked above) | M15 sandbox agents; CI runs \`playwright install --with-deps chromium\` |
| ffmpeg / ffprobe | Ubuntu package on the CI runner (7.1.5 on the course box) | M8, M9, M14 |
| GStreamer | Ubuntu packages on the CI runner (1.28.9 from conda-forge on the course box) | M14 pipeline validator (\`gst-launch-1.0\`, base/good plugins) |

## Site (\`site/pnpm-lock.yaml\`)
| Package | Locked version |
|---|---|
${rows(pnpmVersions("site/pnpm-lock.yaml", "site/package.json"))}

Android SDK packages, installed by \`sdkmanager\` in the CI \`android\` job and on the course box: \`platforms;android-37.0\`, \`build-tools;36.0.0\`, \`platform-tools\`. ML Kit GenAI, ExecuTorch and ONNX Runtime GenAI are not part of the Android build. They are planned in [syllabus](/ai-native-course/syllabus/) section 2.4, and M13 quotes the versions it checked without running them. The Temporal test/dev server binaries are downloaded by the Temporal SDKs at test time and are not pinned here.
`;
writeFileSync(resolve(docs, "reference", "versions.md"), page("Versions", "Pinned versions, generated from the lockfiles.", body));
console.log("generated syllabus.md, changelog.md, reference/versions.md");
