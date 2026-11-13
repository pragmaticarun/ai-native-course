# AI-Native Software Development — Syllabus & Site Outline

**Status:** v0.3, approved by Arunkumar on 13 Nov 2026. Repo created and modules M0–M6 built (see the changelog); everything from M7 onwards is still the plan.
**v0.3 changes (13 Nov 2026, ~20:15 IST):** applied your answers. **(1)** A self-hosted Linux KVM runner runs the emulator jobs (6.8). **(2)** P8 ships **both** the Anthropic and OpenAI computer-use adapters **and** a vendor-neutral reference. **(3)** Kotlin examples are now **Kotlin Multiplatform (KMP)** (shared `commonMain` agent logic, `androidMain`/`jvmMain` backends). **(4)** The reference device is a **Samsung Galaxy A73 5G (Snapdragon 778G, SM7325)**. Gemini Nano, ML Kit GenAI agent/prompt APIs and LiteRT/ExecuTorch NPU paths are **not supported** on it (official device lists, see 2.3.1), so M13/P6 now use a **CPU-first path that runs on the A73** (LiteRT-LM, llama.cpp, ExecuTorch XNNPACK), with GPU as "verify on device" and NPU only as an experimental ORT QNN stretch. Gemini Nano/AgentRunner stays a documented path backed by fakes. Defaults applied for open questions 1, 2, 3 and 5 (marked as defaults in section 7). Answered questions removed from section 7.
**v0.2 changes (13 Nov 2026, ~20:00 IST):** added more depth on Android, on-device AI, multimedia, and computer-use/mobile-use agents. New modules **M13** (on-device & Android agents), **M14** (multimedia & multimodal agents), and **M15** (computer-use & mobile-use agents). Android, media, and GUI-agent worked examples added to M2–M11. **P3** extended. New projects **P6** (on-device Android agent app), **P7** (multimodal media-analysis graph), and **P8** (mobile/computer-use agent graph with eval harness). New research section 2.3, Kotlin/Gradle and native pins in 2.4, plus CI and site updates.
**Prepared:** Friday 13 Nov 2026, ~19:45 IST (v0.1), updated ~20:00 IST (v0.2) and ~20:15 IST (v0.3). All versions and links checked on this date (versions from the PyPI/npm registries and GitHub releases; links checked by HTTP request or by fetching the page).
**Audience:** Experienced systems engineers (C++, Rust, Android, multimedia) who want to build agents and adopt AI-native engineering practices. You can already write software; this course teaches what's new.
**Languages:** Python and TypeScript are the main languages, side by side. **Kotlin** is the main language for the Android/on-device parts (M13, P6, Android pieces of M15/P8). All Kotlin examples are **Kotlin Multiplatform**: agent logic, tool schemas and MCP code live in `commonMain` (Koog and the MCP Kotlin SDK are both multiplatform), and platform backends (LiteRT-LM, ML Kit, llama.cpp JNI) live in `androidMain`/`jvmMain`, so most Kotlin examples also run on the Linux JVM in CI. Each module also has a **"C++/Rust/Kotlin developer notes"** box that maps the new ideas to things you already know (state machines, actors, RAII, back-pressure, fuzzing, etc.).
**Target repo / site:** `pragmaticarun/ai-native-course` → `https://pragmaticarun.github.io/ai-native-course/` (repo created 13 Nov 2026).

---

## 0. Teaching approach

Every lesson follows the same rhythm:

1. **Intuition**: one page with a diagram and an analogy (often a systems analogy, e.g. "an agent loop is an event loop whose scheduler is a language model").
2. **Smallest working example**: under 60 lines, in Python and TS tabs, and runnable offline against a **mock model**, so CI and readers without API keys can run it.
3. **Hands-on**: you change the example, break it, and watch what happens.
4. **Exercises**: 2–4 per lesson, each with **hidden solutions** (collapsed on the site; the solution code is tested in CI).
5. **Module quiz**: 6–10 questions (multiple choice, "spot the bug", or ordering), graded in the browser.

Ground rules for content:
- **No invented frameworks, levels, or statistics.** Every claim about a maturity model or survey links to its primary source. Anything we couldn't verify is labelled as such or left out.
- **Mock first, live second.** Examples default to deterministic test models (Pydantic AI `TestModel`/`FunctionModel`, AI SDK mock providers, LangGraph fake chat models). Each example has a `--live` flag that uses a real provider through env vars. *(Default, confirm in section 7:)* live mode is **provider-agnostic**: the provider and model come from `COURSE_LLM_PROVIDER` / `COURSE_LLM_MODEL` plus that provider's own API-key variable, with no vendor hard-coded in examples.
- **Model-agnostic.** Examples don't hard-code one vendor's model name. Provider and model come from `.env`.

---

## 1. Module map (at a glance)

| # | Module | Lessons | Track |
|---|---|---|---|
| M0 | Orientation, setup & how to use this course | 3 | Foundations |
| M1 | AI maturity models: an honest comparison | 6 | Strategy |
| M2 | LLM and tool-calling foundations | 5 | Agent fundamentals |
| M3 | The agent loop | 5 | Agent fundamentals |
| M4 | Context engineering & memory | 5 | Agent fundamentals |
| M5 | Planning, reflection, multi-agent & human-in-the-loop | 6 | Agent fundamentals |
| M6 | Evals, guardrails, observability, cost & latency | 6 | Agent fundamentals |
| M7 | Agent graphs & orchestration | 6 | Orchestration |
| M8 | Durable execution & production agents | 5 | Orchestration |
| M9 | MCP: servers, clients & tool design | 6 | AI-native programming |
| M10 | Spec-driven development, rules & skills, agent-friendly repos | 6 | AI-native programming |
| M11 | Coding & background agents, TDD with agents, review workflows | 6 | AI-native programming |
| M12 | Team practice changes by maturity level | 4 | AI-native programming / Strategy |
| M13 | **On-device & Android agents** (CPU-first LiteRT-LM / llama.cpp / ExecuTorch on the Galaxy A73; Gemini Nano/ML Kit & AppFunctions as documented paths; ONNX Runtime, quantization, NPUs) | 7 | On-device & media |
| M14 | **Multimedia & multimodal agents** (ffmpeg, GStreamer, speech, vision/video pipelines) | 6 | On-device & media |
| M15 | **Computer-use & mobile-use agents** (screen/a11y observation, computer-use APIs, adb/UI Automator, benchmarks) | 6 | GUI agents |
| — | **Total** | **88 lessons** | |

Projects (Section 5): **P1** coding agent (plan → edit → test → PR), **P2** graph research agent with supervisor + evals, **P3** media MCP server (ffmpeg + GStreamer, Py/TS/Kotlin KMP, plus a real Rust `rmcp` component) + agent client, **P4** durable support/triage workflow, **P5** move a small team project up one maturity level (capstone), **P6** on-device Android agent app with tool calling (LiteRT-LM on CPU on the Galaxy A73 + Koog/KMP; Gemini Nano + AppFunctions as an optional flavour; cloud fallback), **P7** multimodal media-analysis agent graph, **P8** mobile/computer-use agent graph (screenshot → plan → act → verify) with safety checkpoints, Anthropic + OpenAI + vendor-neutral adapters, and an emulator/sandbox eval harness.

Suggested pacing: about 14–16 weeks at 6–8 h/week for everything. M13–M15 can be done right after M9 if Android, media, or GUI agents are the priority. M1 and M12 (strategy) can be read on their own by managers.

---

## 2. Research basis

### 2.1 AI maturity / adoption models (verified)

Only frameworks whose published levels we could read at the source (or, where marked, through reliable secondary sources) are included.

**A. Organisation-wide AI maturity models**

| Framework | Publisher | Year | Levels / structure as published | Source |
|---|---|---|---|---|
| Gartner AI Maturity Model (current wording on Gartner's AI Maturity Assessment page) | Gartner | page current as of 2026 | 5 stages: **Foundational** (ad hoc experimentation) → **Emerging** (early pilots) → **Operational** (AI embedded in select processes, defined ownership) → **Scaled** (deployed across functions, measurable ROI) → **Transformational**. The assessment scores seven pillars (strategy, data, governance, engineering, operating model, culture, AI product/value). | https://www.gartner.com/en/chief-information-officer/research/ai-maturity-model-toolkit (blocks curl; read via a web fetch) |
| Gartner AI Maturity Model (earlier, widely cited wording) | Gartner (original research is paywalled) | c. 2018–2020 | 5 levels: **Awareness → Active → Operational → Systemic → Transformational**. *Secondary source only*: we couldn't open the original Gartner document. | e.g. https://www.usaii.org/ai-insights/understanding-ai-maturity-levels-a-roadmap-for-strategic-ai-adoption |
| MIT CISR Enterprise AI Maturity Model | MIT Center for Information Systems Research (Weill, Woerner, Sebastian) | Dec 2024 | 4 stages: **1 Experiment & Prepare** (28% of firms surveyed) → **2 Build Pilots & Capabilities** (34%) → **3 Develop AI Ways of Working** (31%) → **4 Become AI Future Ready** (7%). Based on a 2022 survey of 721 companies; firms in stages 1–2 had below-average financial performance and firms in stages 3–4 above-average. | https://cisr.mit.edu/publication/2024_1201_EnterpriseAIMaturityModel_WeillWoernerSebastian · https://cisr.mit.edu/content/press-release-enterprise-ai-maturity-121924 |
| Google Cloud AI Adoption Framework | Google Cloud | 2020 | 4 pillars (people, process, technology, data) → 6 themes (**Learn, Lead, Access, Scale, Automate, Secure**). Each theme is assessed in 3 phases: **Tactical → Strategic → Transformational**. | https://services.google.com/fh/files/misc/ai_adoption_framework_whitepaper.pdf · https://cloud.google.com/blog/products/ai-machine-learning/build-a-transformative-ai-capability-with-ai-adoption-framework |
| AWS Cloud Adoption Framework for AI, ML & Generative AI (CAF-AI) | AWS | Feb 2024 (page now marked "for historical reference only") | Not a level ladder. **6 perspectives** (Business, People, Governance, Platform, Security, Operations) of foundational capabilities, plus an adoption cycle **Envision → Align → Launch → Scale**. | https://docs.aws.amazon.com/whitepapers/latest/aws-caf-for-ai/aws-caf-for-ai.html · https://docs.aws.amazon.com/whitepapers/latest/aws-caf-for-ai/your-ai-transformation-journey.html |
| Microsoft Cloud Adoption Framework: AI scenario | Microsoft | living docs (2025–26) | Not a level ladder. A process: AI strategy → plan (use-case identification and prioritisation) → ready → govern → secure → manage, plus a decision tree for choosing Microsoft AI services. | https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ai/strategy · https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ai/plan |
| Accenture "The Art of AI Maturity" | Accenture | 2022 | 4 archetypes on two axes (foundational vs differentiating capability): **AI Achievers, AI Builders, AI Innovators, AI Experimenters**. | https://www.accenture.com/content/dam/system-files/acom/custom-code/ai-maturity/Accenture-Art-of-AI-Maturity-Report-Global-Revised.pdf |
| BCG "The Widening AI Value Gap" (Build for the Future 2025) | BCG | Sep 2025 | Maturity segments: **future-built** (5%), **scaling** (35%), and laggards (60%). Search summaries split the laggards into **emerging** and **stagnating**; the BCG article we fetched only shows the 60% laggard total. | https://www.bcg.com/publications/2025/are-you-generating-value-from-ai-the-widening-gap (blocks curl; read via a web fetch) |

**B. Adoption surveys (useful data, but *not* maturity models; the course will not present them as level models)**

| Survey | Publisher | Date | What it does give us | Source |
|---|---|---|---|---|
| The State of AI in 2025: Agents, innovation, and transformation | McKinsey (QuantumBlack) | 5 Nov 2025 | Experimenting → piloting → scaling phases; 23% of respondents scaling an agentic system somewhere, 39% more experimenting; "AI high performers" ≈ 6%; workflow redesign is a top differentiator. | https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai-2025 |
| The State of AI in the Enterprise (2026 edition) | Deloitte | Jan 2026 | Agentic AI adoption and governance readiness. | https://www.deloitte.com/content/dam/assets-shared/docs/about/2025/state-of-ai-2026-global.pdf |

**C. AI-assisted engineering and agent autonomy levels**

| Framework | Publisher | Year | Levels as published | Source |
|---|---|---|---|---|
| "The Five Levels: from Spicy Autocomplete to the Dark Factory" | Dan Shapiro (blog; widely discussed, e.g. by Simon Willison) | 23 Jan 2026 | Six tiers numbered 0–5, modelled on the NHTSA driving levels. **L0** manual (AI as search, occasional tab-complete) · **L1** offload discrete tasks ("write a unit test") · **L2** pair with an AI-native tool, in flow · **L3** you're a manager reviewing diffs ("almost everyone tops out here") · **L4** you write specs and skills, review plans, leave and check that tests pass · **L5** "dark factory": a black box that turns specs into software. *An opinion piece, not research.* | https://www.danshapiro.com/blog/2026/01/the-five-levels-from-spicy-autocomplete-to-the-software-factory/ · https://simonwillison.net/2026/jan/28/the-five-levels/ |
| Levels of Autonomy for AI Agents | Feng, McDonald & Zhang (Knight First Amendment Institute; arXiv 2506.12469) | 2025 | 5 levels defined by the **user's role**: **L1 Operator → L2 Collaborator → L3 Consultant → L4 Approver → L5 Observer**. Treats autonomy as a design choice separate from capability. | https://arxiv.org/abs/2506.12469 · https://www.knightcolumbia.org/content/levels-of-autonomy-for-ai-agents-1 |
| DORA AI Capabilities Model (from the 2025 State of AI-assisted Software Development) | DORA / Google Cloud | 2025 | Not levels: **7 capabilities** that amplify AI benefits: clear and communicated AI stance; healthy data ecosystems; AI-accessible internal data; strong version control; working in small batches; user-centric focus; quality internal platforms. Core finding: "AI is an amplifier". | https://dora.dev/research/2025/dora-report/ · https://dora.dev/ai/capabilities-model/report/ · https://services.google.com/fh/files/misc/2025_dora_ai_capabilities_model.pdf |
| DORA ROI of AI-assisted Software Development | DORA | Apr 2026 | ROI framework and calculator (no annual survey in 2026, according to secondary reports). | https://dora.dev/ai/roi/report/ |
| Thoughtworks Technology Radar, Vol. 35 | Thoughtworks | 4 Nov 2026 | Not levels. Themes: harness engineering at scale, keeping human judgment as agents multiply (warns against "human-in-the-loop theater"), choosing beyond frontier models, AI economics. Adopt ring includes agent sandboxing and threat modeling. | https://www.thoughtworks.com/en-us/about-us/news/2026/thoughtworks-technology-radar-highlights-stronger-controls · https://www.thoughtworks.com/radar · https://www.thoughtworks.com/en-us/radar/techniques/agent-sandboxing |

**How M1 frames the comparison:**
- *Ladders* (Gartner, MIT CISR, BCG, Shapiro, Feng et al.) versus *capability maps* (Google themes, AWS perspectives, DORA capabilities, Microsoft process). Ladders are good for saying where you are; maps are good for deciding what to fix next.
- *Organisation scope* (Gartner/MIT/BCG/Accenture/Google/AWS/Microsoft) versus *engineering-team scope* (Shapiro, DORA, Thoughtworks) versus *single-agent design scope* (Feng et al.).
- Caveats we teach explicitly: vendor frameworks steer you toward that vendor's products; survey-derived segments depend on self-reported data; Shapiro's levels are one practitioner's opinion; the Gartner stage names have changed over time.
- The course's **working ladder** for the team-practice modules (M12, P5) is Shapiro's L0–L5 for the engineering workflow, *combined with* DORA's 7 capabilities as the prerequisites for moving up. The course will say plainly that this is our synthesis, not a published standard.

### 2.2 Tooling snapshot (checked 13 Nov 2026)

Versions are the latest on PyPI/npm on 13 Nov 2026 (release date in brackets).

**Agent frameworks**

| Tool | Python | TypeScript | Notes |
|---|---|---|---|
| LangGraph | `langgraph 1.2.21` (2026-11-12), `langchain-core 1.8.0` | `@langchain/langgraph 1.7.4`, `@langchain/core 1.4.0` | Graph/state-machine orchestration; checkpointers and durable execution built in. Docs: https://docs.langchain.com/oss/python/langgraph/overview |
| OpenAI Agents SDK | `openai-agents 0.24.0` (2026-10-15) | `@openai/agents 0.22.0` (2026-11-12) | Agents, handoffs, guardrails, sessions, tracing. Still 0.x, so pin exactly. https://openai.github.io/openai-agents-python/ · https://openai.github.io/openai-agents-js/ |
| Claude Agent SDK | `claude-agent-sdk 0.2.181` (2026-11-12) | `@anthropic-ai/claude-agent-sdk 0.3.323` (2026-11-12) | The Claude Code agent harness as a library; very frequent releases. https://docs.claude.com/en/docs/agent-sdk/overview |
| Pydantic AI | `pydantic-ai 2.68.0` (2026-11-12) | — | Type-safe agents; `TestModel`/`FunctionModel` for offline tests; built-in Temporal/DBOS durable execution. https://ai.pydantic.dev/ |
| Vercel AI SDK | — | `ai 7.0.172`, `@ai-sdk/openai 4.0.117`, `@ai-sdk/anthropic 4.0.104` | TS toolkit for tool calling, streaming, and agent loops. https://ai-sdk.dev/docs/introduction |
| Mastra | — | `@mastra/core 1.83.0` (2026-11-12) | TS agent framework (agents, workflows, memory, evals). https://mastra.ai/docs |
| Provider SDKs | `openai 3.50.0`, `anthropic 2.8.0`, `litellm 1.109.1` | — | Used in M2 to show the raw API before any framework. |

**MCP (Model Context Protocol)**
- **Current spec revision: `2026-07-28`** (latest GitHub release of `modelcontextprotocol/modelcontextprotocol`, 28 Jul 2026; previous revision `2025-11-25`). Big changes: a **stateless protocol** (no `initialize` handshake; version and capabilities travel in `_meta` on every request), new `server/discover`, no protocol-level sessions or `Mcp-Session-Id`, `subscriptions/listen` replaces GET/subscribe, the **Multi Round-Trip Requests** (`input_required`) pattern replaces server-initiated sampling/elicitation/roots requests, tasks moved into an official extension, and **Roots, Sampling, and Logging are deprecated**. Changelog: https://modelcontextprotocol.io/specification/2026-07-28/changelog
- **Python SDK:** `mcp 2.3.0` (2026-10-02), with v1.x maintenance continuing (`v1.30.0`). Docs: https://py.sdk.modelcontextprotocol.io/
- **TypeScript SDK:** v2 is split into packages: `@modelcontextprotocol/server 2.4.0`, `@modelcontextprotocol/client 2.4.0`, `@modelcontextprotocol/core 2.4.0`, `@modelcontextprotocol/node 2.1.2`, and `@modelcontextprotocol/codemod`. The old monolithic `@modelcontextprotocol/sdk` is at `1.32.2` (v1 line). v2.4.0 adds experimental "Skills over MCP" (SEP-2640).
- Others: `fastmcp 4.1.8` (Python, PrefectHQ); `@modelcontextprotocol/inspector 2.15.0` (debugging UI).
- Governance: MCP and AGENTS.md were contributed to the Linux Foundation's **Agentic AI Foundation (AAIF)**: https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation

**Durable execution**
- Temporal: `temporalio 1.36.0` (Py); `@temporalio/client`/`@temporalio/workflow 1.25.0` (TS). Official OpenAI Agents SDK integration: https://docs.temporal.io/develop/python/integrations/openai-agents
- Pydantic AI durable execution (Temporal, DBOS, and others): https://pydantic.dev/docs/ai/capabilities/durable_execution/temporal/
- DBOS: `dbos 3.5.0` (Postgres-backed durable workflows). https://docs.dbos.dev/
- Restate: `restate-sdk 1.5.1` (Py), `@restatedev/restate-sdk 1.18.3` (TS). Inngest: `inngest 4.26.2` (TS).
- LangGraph durable execution / checkpointing: https://docs.langchain.com/oss/python/langgraph/durable-execution

**Evals and observability**
- `inspect-ai 0.3.289` (UK AISI; https://inspect.aisi.org.uk/), `deepeval 4.3.4`, `promptfoo 0.125.1` (npm CLI; https://www.promptfoo.dev/docs/intro/), `ragas 0.4.3`, `autoevals 0.4.1` (npm), `braintrust 0.50.0`, `langsmith 0.14.17`, `arize-phoenix 21.0.0`, `logfire 5.6.0`. Note: `evalite` (npm 0.19.0) and `@inngest/agent-kit` (0.13.2) haven't been released in about a year, so they're **not** recommended.

**Spec-driven development**
- **GitHub Spec Kit**: latest release `v1.4.0` (10 Nov 2026), CLI `specify`. https://github.com/github/spec-kit. Install from the GitHub repo (`uvx --from git+https://github.com/github/spec-kit.git@v1.4.0 specify ...`). There is a PyPI package `specify-cli 1.4.0`, but its metadata doesn't link to GitHub, so we couldn't confirm it's official; don't use it until confirmed.
- **Kiro** (AWS): specs as `requirements.md` → `design.md` → `tasks.md`, with requirements-first and design-first variants, plus "quick spec". https://kiro.dev/docs/specs/

**Coding & background agents (CLI versions from npm, 13 Nov 2026)**
- Claude Code `@anthropic-ai/claude-code 2.1.323`, https://docs.claude.com/en/docs/claude-code/overview
- OpenAI Codex CLI `@openai/codex 0.169.0`; Codex cloud: https://developers.openai.com/codex/cloud
- GitHub Copilot CLI `@github/copilot 1.0.111`; Copilot coding agent (assign an issue, get a PR): https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-coding-agent
- Gemini CLI `@google/gemini-cli 0.68.0`
- Cursor (IDE agent and cloud/background agents), Devin, and others are covered conceptually. *Unverified:* a third-party ranking says Google Jules is being shut down after 11 Nov 2026. Confirm with Google before the course says anything about Jules.

**Rules & skills files**
- **AGENTS.md**: an open Markdown format for agent instructions, now stewarded by AAIF. https://agents.md/
- **Cursor rules**: `.cursor/rules/*.mdc` with frontmatter (always / glob / agent-requested / manual); Cursor also reads AGENTS.md, including nested files. https://cursor.com/docs/rules
- **Agent Skills** (`SKILL.md` folders with YAML frontmatter `name`/`description`, plus optional scripts and resources loaded progressively). Started by Anthropic and donated to AAIF as an open standard. https://agentskills.io/specification · https://www.anthropic.com/news/donating-agent-skills-to-the-agentic-ai-foundation · Claude Code skills docs: https://code.claude.com/docs/en/skills

### 2.3 Android, on-device, multimedia & GUI-agent tooling (checked 13 Nov 2026)

Versions come from Google Maven (`dl.google.com/android/maven2`), Maven Central, PyPI, npm, and GitHub releases, all queried on 13 Nov 2026. Every link was checked (HTTP 200 or page fetched).

**Gemini Nano / ML Kit GenAI / AICore**
- ML Kit GenAI APIs run Gemini Nano on-device through **AICore**, an Android system service. There are task APIs (summarization, proofreading, rewriting, image description, speech recognition) plus **direct model access** (Prompt API, `com.google.mlkit:genai-prompt`, latest `1.0.0-beta5`; docs show beta4). https://developers.google.com/ml-kit/genai · https://developers.google.com/ml-kit/genai/prompt/android/get-started
- Documented limits we'll teach: input under about 4,000 tokens; API 26+; inference only while the app is the top foreground app (`BACKGROUND_USE_BLOCKED`); per-app quotas (`BUSY`, `PER_APP_BATTERY_USE_QUOTA_EXCEEDED`); not supported on unlocked bootloaders; outputs differ across Gemini Nano versions (`getBaseModelName()`). The structured-output API is **alpha** and needs KSP 2.3.6+.
- **On-device agents:** `com.google.mlkit:genai-agent` (`1.0.0-alpha1`) adds `AgentRunner`, a tool-calling loop described as observe → reason → act → evaluate with `maxTurns`. Tools are **Android AppFunctions** (`@AppFunctionDeclaration`), can be restricted to the app with `ACCESS_LEVEL_SELF`, and support a decorator pattern for human-in-the-loop confirmation. https://developers.google.com/ml-kit/genai/agent/android · https://developers.google.com/ml-kit/genai/agent/android/define-tools
- Model tiers (per Firebase docs): `STABLE` (e.g. Gemini Nano 3 `nano-v3` / `nano-v2`), `PREVIEW` (Gemini Nano 4 Full, based on Gemma 4 E4B), and `PREVIEW_FAST` (Nano 4 Fast, based on Gemma 4 E2B). https://firebase.google.com/docs/ai-logic/hybrid/android/configuration-options

**AppFunctions (Android's on-device MCP-equivalent)**
- Platform API plus Jetpack library (`androidx.appfunctions`; latest `1.0.0-rc01`, while ML Kit's agent docs pin `1.0.0-alpha13`). Lets apps expose typed functions as tools to authorised callers (`EXECUTE_APP_FUNCTIONS`). Android 16+. **Experimental**; Gemini integration is in private preview. Test with `adb shell cmd app_function list-app-functions`. https://developer.android.com/ai/appfunctions

**Firebase AI Logic hybrid inference**
- `com.google.firebase:firebase-ai` `18.2.0` + `firebase-ai-ondevice` `16.0.0-beta08` (BoM `35.2.0`; the on-device SDK isn't in the BoM). Inference modes: `PREFER_ON_DEVICE`, `ONLY_ON_DEVICE`, `PREFER_IN_CLOUD`, `ONLY_IN_CLOUD`. On-device side is single-turn only (text, or text plus one image, or structured output), validated for English and Korean, with output under about 256 tokens recommended. App Check is used for the cloud side. https://firebase.google.com/docs/ai-logic/hybrid/android/get-started · https://developer.android.com/ai/hybrid

**Google AI Edge**
- **LiteRT** `2.3.2` (GitHub/Google Maven; Python `ai-edge-litert 2.3.0`). The `CompiledModel` API handles CPU/GPU/NPU. **NPU vendors:** Qualcomm AI Engine Direct (AOT plus on-device compilation; SM8450 → SM8850), MediaTek NeuroPilot (Dimensity 7300 → 9500), Google Tensor (AOT only, beta), Intel OpenVINO, and Samsung Exynos. Delivery through Google Play for On-device AI; from 2.3.0, NPU runtime libraries ship as Maven packages. https://developers.google.com/edge/litert/next/npu · https://developer.android.com/ai/custom
- **LiteRT-LM** `0.19.1` (`com.google.ai.edge.litertlm:litertlm-android`; also a JVM artifact). Kotlin `Engine` / `Conversation` with streaming `Flow`. Uses `.litertlm` models and supports GPU/NPU, multimodality, and tool use. The docs say to initialise off the main thread. Gemma 4 models are listed. https://developers.google.com/edge/litert-lm/android · https://developers.google.com/edge/litert-lm/models/gemma-4 · https://github.com/google-ai-edge/LiteRT-LM
- **MediaPipe LLM Inference API is now maintenance-only.** Its Java `LlmInference` class is `@Deprecated` in favour of LiteRT-LM (`tasks-genai` `0.10.35`). We cover it only for migration. MediaPipe Tasks vision/audio stay current at `1.2.3`. https://developers.google.com/edge/mediapipe/solutions/genai/llm_inference
- **LiteRT Torch** PyTorch → LiteRT export: PyPI `litert-torch 0.10.0`, matching GitHub `google-ai-edge/ai-edge-torch` v0.10.0. The old `ai-edge-torch` PyPI name stopped at 0.7.2 (Jan 2026); we infer a rename. Google AI Edge Gallery sample app `1.0.23`. https://github.com/google-ai-edge/gallery

**Android Studio & Android CLI for agents**
- **Gemini in Android Studio Agent Mode:** plan + tools + permission prompts; parallel conversations; **MCP servers** over remote HTTP only (stdio, resources, and prompt templates are not supported); **AGENTS.md** (`GEMINI.md` takes precedence in the same directory); skills; device tools (deploy, screenshot, Logcat, interact with the running app); local/remote third-party models; "Journeys" natural-language E2E tests (Studio Labs). https://developer.android.com/studio/gemini/agent-mode · https://developer.android.com/studio/gemini/add-mcp-server · https://developer.android.com/studio/gemini/agent-files · https://developer.android.com/studio/gemini/features
- **Android CLI** (preview): `android create`, `android sdk install`, `android emulator`, `android run`, `screen capture --annotate` (labelled UI elements), `android layout` (layout tree as JSON), and Android Device Streaming over ADB-over-SSL. Android skills are `SKILL.md` files, with official plugins for Claude Code, Codex, and Antigravity. https://developer.android.com/cli · https://developer.android.com/tools/agents/android-cli/agent-plugins · https://developer.android.com/blog/posts/android-cli-device-streaming-and-skills

**Kotlin agent frameworks & MCP SDKs**
- **JetBrains Koog** `1.3.0` (Maven Central `ai.koog:koog-agents`; Koog 1.0 shipped May 2026). Kotlin/Java agents with graph strategies, tools, persistence, history compression, MCP and ACP integration, and Kotlin Multiplatform (Android included). Since 1.0 it can run LiteRT models locally on Android. The MCP module `ai.koog:agents-mcp` is still `1.3.0-beta`. https://docs.koog.ai/ · https://github.com/JetBrains/koog · https://blog.jetbrains.com/ai/2026/05/koog-1-0-is-out-stable-core-better-interop-and-multiplatform-observability/
- **MCP Kotlin SDK** `0.16.0` (`io.modelcontextprotocol:kotlin-sdk`) · **MCP Rust SDK** `rmcp` `3.10.0`. https://github.com/modelcontextprotocol/kotlin-sdk · https://github.com/modelcontextprotocol/rust-sdk

**General on-device runtimes**

| Runtime | Version (13 Nov 2026) | Notes |
|---|---|---|
| llama.cpp / ggml | **v1.0.0** (released 13 Nov 2026) | First 1.0: removed 35 deprecated `llama.h` functions; GGUF quantization; `mtmd` multimodal (vision/audio); `llama-server` with MCP tool cancellation. https://github.com/ggml-org/llama.cpp · https://huggingface.co/blog/ggml-org/llama-cpp-v1 |
| whisper.cpp | v1.9.5 | On-device ASR (C/C++). https://github.com/ggml-org/whisper.cpp |
| ExecuTorch | v1.6.0 (PyPI `executorch 1.6.0`; Maven `org.pytorch:executorch-android` **1.5.1**) | PyTorch's on-device runtime. https://docs.pytorch.org/executorch/stable/index.html |
| ONNX Runtime / ORT GenAI | ORT 1.32.0 (PyPI + `onnxruntime-android`); `onnxruntime-genai` 0.19.0 | GenAI loop on top of ORT; QNN execution provider for Qualcomm NPUs. https://onnxruntime.ai/docs/genai/ · https://onnxruntime.ai/docs/execution-providers/QNN-ExecutionProvider.html |
| MLC LLM | **not verified** | Docs are live (https://llm.mlc.ai/docs/), but there are no stable GitHub releases (only a 2023 pre-release tag) and no PyPI package. Covered conceptually only. |
| Python/JS bindings | `llama-cpp-python 0.3.36` (1 Oct 2026), `node-llama-cpp 3.22.3`, `@huggingface/transformers 4.3.2`, `onnxruntime-node 1.31.1` | Compatibility of `llama-cpp-python` with llama.cpp v1.0.0 is **not verified**. |
| Quantization tooling | `torchao 0.18.0`, `optimum 2.3.0`, `transformers 5.23.0`, `torch 2.15.0`; llama.cpp `llama-quantize` | https://github.com/pytorch/ao · https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md |

**Multimedia**
- **FFmpeg 9.0.2 "Lei"** is the newest release listed on https://ffmpeg.org/download.html (8.1.3 and 8.0.3 are also listed). Filters reference: https://ffmpeg.org/ffmpeg-filters.html. Python: `av` (PyAV) `19.0.2`. *Not recommended:* `ffmpeg-python` (last release 2019).
- **GStreamer 1.28.9** (released 6 Nov 2026). The 1.28 series adds ML inference elements, e.g. `onnxinference` + `tensordecodebin`. Python bindings: `PyGObject 3.58.1`. https://gstreamer.freedesktop.org/releases/1.28/ · https://gstreamer.freedesktop.org/documentation/onnx/index.html · https://www.collabora.com/news-and-blog/news-and-events/gstreamer-128-brings-ai-inference-to-your-media-pipeline.html
- Android media: Jetpack **Media3** (ExoPlayer/Transformer) stable `1.11.1`; **CameraX** stable `1.6.2`. https://developer.android.com/media/media3
- Audio/vision helpers: `faster-whisper 1.2.1`, `pywhispercpp 1.5.1`, `silero-vad 6.2.3`, `pyannote.audio 4.0.7`, `scenedetect 0.7.3`, `opencv-python-headless 5.0.0.93`, `mediapipe 1.2.3`.
- Multimodal open model for on-device work: **Gemma 4 E2B / E4B** (text, image, and audio input via LiteRT-LM; video goes in as sampled frames). https://huggingface.co/google/gemma-4-E2B-it

**2.3.1 Reference device: Samsung Galaxy A73 5G — what actually runs on it (checked 13 Nov 2026)**

| Item | Finding | Source |
|---|---|---|
| SoC / memory | Snapdragon 778G (6 nm, octa-core 2.4 + 1.8 GHz), 6 GB or 8 GB RAM depending on variant; launched on Android 12 with "software updates up to 4 years" (Samsung India newsroom) | Samsung: https://www.samsung.com/ph/smartphones/galaxy-a/galaxy-a73-5g-awesome-white-128gb-sm-a736bzwdphl/ · https://news.samsung.com/in/samsung-revamps-galaxy-a-series-unveils-five-new-smartphones-in-india |
| GPU / NPU | Adreno 642L (OpenGL ES 3.2, **OpenCL 2.0 FP**, Vulkan 1.1); Hexagon 770 (tensor/vector/scalar accelerators) | Qualcomm: https://www.qualcomm.com/smartphones/products/7-series/snapdragon-778g-5g-mobile-platform |
| Chip ID | SM7325; Qualcomm's SNPE/QAIRT runtime table lists it with CPU ✓, GPU ✓, DSP/HTP **Hexagon V68**, no AIP | https://docs.qualcomm.com/doc/80-63442-10/topic/SNPE_general_overview.html?product=1601111740010412 |
| **Gemini Nano / ML Kit GenAI (Prompt API, agent API, summarize/proofread/rewrite/image description)** | **Not supported.** The A73 isn't on the supported-device lists; the only Samsung entries are Galaxy S25/S26, Z Flip7/8, Z Fold7/8, Tab S12 and TriFold. | https://developers.google.com/ml-kit/genai |
| ML Kit `genai-agent` (`AgentRunner`) | **Not supported.** Needs a listed device on Android 14+ enrolled in the AICore Developer Preview. | https://developer.android.com/ai/gemini-nano/mlkit-agent-api |
| ML Kit GenAI speech recognition | **Basic mode: supported** (any Android device on API 31+; the A73 shipped with Android 12 = API 31). **Advanced mode: not supported** (needs Pixel 10/11 or SM8750/SM8845/SM8850/SM8950/SM8975, Dimensity MT6991/3/5, Exynos 2600). | https://developers.google.com/ml-kit/genai/speech-recognition/android |
| Firebase AI Logic hybrid | On-device half needs Gemini Nano, so on the A73 `PREFER_ON_DEVICE` will take the **cloud** path; `ONLY_ON_DEVICE` won't work. *(Inferred from the Nano device list; check the fallback on the device.)* | https://firebase.google.com/docs/ai-logic/hybrid/android/get-started |
| LiteRT NPU (Qualcomm AI Engine Direct) | **Not supported.** Qualcomm list: SM8450, SM8475, SM8550, SM8650, SM8750, SM8850. | https://developers.google.com/edge/litert/next/qualcomm |
| ExecuTorch Qualcomm (QNN) backend | **Not supported.** SM7325 isn't in the `QcomChipset` enum on `main` (checked 13 Nov 2026). | https://github.com/pytorch/executorch/blob/main/backends/qualcomm/serialization/qc_compiler_spec.fbs · https://docs.pytorch.org/executorch/stable/backends-qualcomm.html |
| ONNX Runtime QNN EP (HTP) | **Possible, not verified on the A73.** ORT documents testing on SM8350 (also HTP V68). HTP needs quantized models. An issue reports V68 context binaries compiled on an x86 host failing on the device, while compiling on the device worked (issue closed). `onnxruntime-qnn` is published for Android ARM64. | https://onnxruntime.ai/docs/execution-providers/QNN-ExecutionProvider.html · https://github.com/microsoft/onnxruntime/issues/26686 · https://github.com/onnxruntime/onnxruntime-qnn |
| llama.cpp OpenCL (Adreno) | **Not on the verified list.** Verified Adreno GPUs: 750, 810, 830, 840, X1-85, X2-90. CPU (arm64 NEON) is the safe path. | https://github.com/ggml-org/llama.cpp/blob/master/docs/backend/OPENCL.md · https://github.com/ggml-org/llama.cpp/blob/master/docs/android.md |
| LiteRT-LM | **CPU path (XNNPACK) is the baseline.** GPU uses LiteRT's GPU stack; the Adreno 642L supports OpenCL 2.0 and Vulkan 1.1, but no A73/778G result is published, so the course treats it as **verify on device**. Published Gemma 4 E2B numbers are for the S26 Ultra (CPU: 2,583 MB file, ~1.7 GB peak CPU memory). | https://developers.google.com/edge/litert-lm/android · https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm |
| ExecuTorch XNNPACK (CPU) | Supported on Android arm64 (generic ARM CPU backend). | https://docs.pytorch.org/executorch/stable/backends-xnnpack.html |

**Model ladder for the A73 (all published as LiteRT-LM community models):** `litert-community/functiongemma-270m-ft-mobile-actions` (small function-calling model fine-tuned for mobile actions; see Google's AI Edge Gallery post https://developers.googleblog.com/on-device-function-calling-in-google-ai-edge-gallery/ and base model https://huggingface.co/google/functiongemma-270m-it) → `litert-community/Gemma3-1B-IT` → `litert-community/gemma-4-E2B-it-litert-lm` (on 8 GB devices; RAM headroom and speed to be measured on the A73 in L13.7). Equivalent small GGUF models are used for the llama.cpp path. **No A73 speed numbers are quoted anywhere in the course until we measure them ourselves.**

**Computer-use & mobile-use**
- **Anthropic computer use:** `computer_toolset_20260801` is the stable, client-executed toolset with no beta header. It has 17 member tools (`screenshot`, `left_click`, `type`, `zoom`, …) and supports batched actions. Successor to beta `computer_20251124` / `computer_20250124`. Plus a new `browser_toolset_20260801`. https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool · https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-reference
- **OpenAI computer use (Responses API):** `tools: [{type: "computer"}]` returns `computer_call` items with ordered `actions` (`click`, `double_click`, `drag`, `move`, `scroll`, `keypress`, `type`, `wait`, `screenshot`). You reply with `computer_call_output` screenshots. The docs also recommend a code-execution approach (Playwright/PyAutoGUI) for their newest model, and the SDK ships `ComputerToolset` / `BrowserToolset` helpers with `before_action` / `confirm` hooks. https://developers.openai.com/api/docs/guides/tools-computer-use
- **Browser automation:** Playwright `1.65.x` (PyPI 1.65.1 / npm 1.65.0), `@playwright/mcp 0.0.85`, `browser-use 1.0.3`. Sandboxes: `e2b-desktop 2.7.2`, trycua/cua (`cua-agent 0.9.1`).
- **Android UI automation:** `adb` (screencap, `input`, `uiautomator dump`) https://developer.android.com/tools/adb · UI Automator https://developer.android.com/training/testing/other-components/ui-automator · Accessibility tree (`AccessibilityNodeInfo`) https://developer.android.com/reference/android/view/accessibility/AccessibilityNodeInfo · `uiautomator2 3.7.1`, `adbutils 2.12.0` (Python) · `@mobilenext/mobile-mcp 1.0.17` (MCP server for mobile automation) · DroidRun `0.7.4` · minitap `mobile-use` (PyPI `minitap-mobile-use 4.0.0`, but GitHub's latest release is `v3.3.0`; see unverified list) · Appium `3.9.0`.
- **Benchmarks:** **AndroidWorld**: 116 parameterised tasks across 20 apps on a live emulator (Pixel 6, API 33 AVD, launched with `-grpc 8554`), durable state-based rewards, installed from source (Python 3.11+). https://github.com/google-research/android_world · **OSWorld / OSWorld-Verified**: real Ubuntu desktop tasks, execution-based evaluation (`desktop-env 1.0.3`). https://github.com/xlang-ai/OSWorld · https://xlang.ai/blog/osworld-verified · **WebArena**: self-hosted web environments. https://github.com/web-arena-x/webarena. *Leaderboard numbers are mostly self-reported or come from aggregators. The course won't quote them.*

### 2.4 Proposed pinned versions for the course

Pin exact versions in `uv.lock` / `pnpm-lock.yaml`. Renovate opens a PR when a new version comes out, and that PR only merges if the CI suite passes. Each bump gets an entry on the changelog page.

**Runtime:** Python **3.13** (CI matrix also runs 3.14), Node.js **24 LTS**, `uv 0.13.8`, `pnpm 12.18.0`, TypeScript `7.0.2`.

`python/pyproject.toml` (proposed):
```toml
[project]
requires-python = ">=3.13"
dependencies = [
  "pydantic==2.14.3",
  "pydantic-ai==2.68.0",
  "langgraph==1.2.21",
  "langchain-core==1.8.0",
  "openai-agents==0.24.0",
  "claude-agent-sdk==0.2.181",
  "openai==3.50.0",
  "anthropic==2.8.0",
  "mcp==2.3.0",
  "fastmcp==4.1.8",
  "temporalio==1.36.0",
  "dbos==3.5.0",
  "inspect-ai==0.3.289",
  "deepeval==4.3.4",
  "logfire==5.6.0",
]
[dependency-groups]
dev = ["pytest==9.2.0", "pytest-asyncio==1.5.0", "ruff==0.17.5", "mypy==2.4.1"]
```

`ts/package.json` (proposed):
```json
{
  "engines": { "node": ">=24" },
  "dependencies": {
    "ai": "7.0.172",
    "@ai-sdk/openai": "4.0.117",
    "@ai-sdk/anthropic": "4.0.104",
    "@mastra/core": "1.83.0",
    "@langchain/langgraph": "1.7.4",
    "@langchain/core": "1.4.0",
    "@openai/agents": "0.22.0",
    "@anthropic-ai/claude-agent-sdk": "0.3.323",
    "@modelcontextprotocol/server": "2.4.0",
    "@modelcontextprotocol/client": "2.4.0",
    "@modelcontextprotocol/node": "2.1.2",
    "@temporalio/client": "1.25.0",
    "@temporalio/workflow": "1.25.0",
    "@temporalio/worker": "1.25.0",
    "zod": "4.6.7"
  },
  "devDependencies": {
    "typescript": "7.0.2", "vitest": "5.1.0", "tsx": "4.23.15", "promptfoo": "0.125.1"
  }
}
```

Site: `astro 7.4.11`, `@astrojs/starlight 0.42.11`, `starlight-links-validator 0.27.0`.

**Optional dependency groups for M13–M15 / P3, P6–P8** (in `python/pyproject.toml`, so the core install stays light):
```toml
[dependency-groups]
media = [
  "av==19.0.2", "PyGObject==3.58.1", "faster-whisper==1.2.1", "pywhispercpp==1.5.1",
  "silero-vad==6.2.3", "scenedetect==0.7.3", "opencv-python-headless==5.0.0.93", "mediapipe==1.2.3",
]
ondevice = [
  "llama-cpp-python==0.3.36", "onnxruntime==1.32.0", "onnxruntime-genai==0.19.0",
  "executorch==1.6.0", "ai-edge-litert==2.3.0", "litert-torch==0.10.0",
  "torch==2.15.0", "torchao==0.18.0", "transformers==5.23.0", "optimum==2.3.0",
]
cua = [
  "playwright==1.65.1", "browser-use==1.0.3", "uiautomator2==3.7.1", "adbutils==2.12.0",
  "desktop-env==1.0.3",
  # AndroidWorld: installed from source at a pinned git SHA (no PyPI package)
]
```
`ts/package.json` additions: `"playwright": "1.65.0"`, `"@playwright/mcp": "0.0.85"`, `"@mobilenext/mobile-mcp": "1.0.17"`, `"node-llama-cpp": "3.22.3"`, `"@huggingface/transformers": "4.3.2"`.

**Native / system (pinned in Dockerfiles, built or downloaded by tag):** FFmpeg `9.0.2`, GStreamer `1.28.9` (Ubuntu's packaged versions lag, so CI uses a container), llama.cpp `v1.0.0`, whisper.cpp `v1.9.5`, ExecuTorch `v1.6.0`, ONNX Runtime `1.32.0` / ORT GenAI `0.19.0`, LiteRT `2.3.2`, LiteRT-LM `0.19.1`, MediaPipe `1.2.3`. Rust: `rmcp = "3.10.0"`.

**Android (`android/gradle/libs.versions.toml`, proposed):**
```toml
[versions]
kotlin = "2.4.21"            # latest stable (2.5.0-RC exists)
agp = "9.5.1"                # latest stable (9.6.0-alpha exists)
composeBom = "2026.09.00"
coroutines = "1.11.0"
coreKtx = "1.19.1"
koog = "1.3.0"               # agents-mcp is 1.3.0-beta
mcpKotlin = "0.16.0"
mlkitGenaiPrompt = "1.0.0-beta5"
mlkitGenaiAgent = "1.0.0-alpha1"
appfunctions = "1.0.0-alpha13"   # version ML Kit's agent docs pair with genai-agent; 1.0.0-rc01 exists, compatibility untested
mlkitGenaiSummarization = "1.0.0-beta1"
mlkitGenaiImageDescription = "1.0.0-beta1"
mlkitGenaiSpeech = "1.0.0-alpha2"
firebaseBom = "35.2.0"
firebaseAi = "18.2.0"
firebaseAiOndevice = "16.0.0-beta08"
litertlm = "0.19.1"
litert = "2.3.2"
mediapipeTasks = "1.2.3"     # tasks-vision / tasks-audio
mediapipeGenai = "0.10.35"   # deprecated LLM Inference API, migration lesson only
media3 = "1.11.1"
camerax = "1.6.2"
executorch = "1.5.1"         # Maven lags the 1.6.0 GitHub/PyPI release
onnxruntimeAndroid = "1.32.0"
```
Rule: only stable versions, unless the API exists only as alpha/beta (ML Kit GenAI, AppFunctions, Firebase on-device). Those lessons carry a visible **"preview API"** badge.

---

## 3. Modules in detail

Notation: **L** = lesson, **WE** = worked example, **Ex** = exercise (solution hidden), **Q** = quiz.

### M0 — Orientation, setup & how to use this course (3 lessons)
- **L0.1** What "AI-native" means here: building *with* agents and building agents.
- **L0.2** Setting up the environment on Ubuntu: `uv`, Node 24 + pnpm, `.env` provider config, mock vs live mode, Docker for Temporal/Postgres.
- **L0.3** How exercises, hidden solutions, quizzes, and the "verify-in-CI" promise work.
- **WE:** run the hello-agent in both languages, mock and then live.
- **Ex:** switch providers through env vars only; make the mock model return a scripted tool call.
- **Q:** 5 questions.
- *C++/Rust notes:* the `uv` lockfile ≈ `Cargo.lock`; pnpm workspaces ≈ Cargo workspaces.

### M1 — AI maturity models: an honest comparison (6 lessons)
- **L1.1** Why maturity models exist, and how they mislead (ladders vs maps; vendor bias; self-reported surveys).
- **L1.2** Organisation ladders: Gartner (both wordings), MIT CISR, BCG, Accenture archetypes.
- **L1.3** Cloud-vendor capability maps: Google AI Adoption Framework, AWS CAF-AI, Microsoft CAF AI scenario.
- **L1.4** Engineering-team views: DORA AI Capabilities Model and "AI as amplifier"; Thoughtworks Radar Vol. 35 themes.
- **L1.5** Autonomy levels: Shapiro L0–L5 (coding workflow) vs Feng et al. L1–L5 (user role in an agent product).
- **L1.6** Building your own assessment: the course's working ladder (Shapiro + DORA prerequisites), clearly labelled as our synthesis.
- **WE:** a side-by-side mapping table and a self-assessment worksheet (YAML → radar chart rendered on the site).
- **Ex:** (1) place three described teams on two different models and explain why the placements differ; (2) find the vendor-specific assumptions in one framework; (3) write a one-page "next level" plan for your own team.
- **Q:** 8 questions (e.g. "Which framework is a capability map, not a ladder?").
- *C++/Rust notes:* compare with CMMI and SAE/NHTSA autonomy levels: the same idea of naming levels so people share a vocabulary.

### M2 — LLM and tool-calling foundations (5 lessons)
- **L2.1** Tokens, context windows, sampling, and what's non-deterministic (intuition: a stochastic pure function).
- **L2.2** Raw provider APIs: messages, system prompts, streaming (Python `openai`/`anthropic`; TS AI SDK).
- **L2.3** Structured output: JSON Schema, Pydantic / Zod validation, retry on validation failure.
- **L2.4** Tool calling end to end: schema → model picks a tool → you execute it → result goes back to the model.
- **L2.5** Prompt caching, batching, and token accounting basics.
- **WE:** a "unit-converter" tool, built raw first and then with Pydantic AI and the AI SDK.
- **WE (Android, KMP):** the same structured-output idea in Kotlin: extract `{title, date, location}` from a notification string. The `commonMain` code depends on a small `OnDeviceLlm` interface. The **A73 path** uses LiteRT-LM on CPU (Gemma 3 1B) with JSON-schema validation and a repair retry. The **documented Gemini Nano path** (ML Kit Prompt API `genai-prompt`: ~4k-token input limit, `countTokens`, `BUSY` handled with exponential backoff) runs only on supported devices; on the A73 and in CI it's exercised through a fake that replays recorded Nano responses and error codes.
- **WE (multimodal):** send an image (a video frame grabbed with ffmpeg) plus a question. Covers token cost per image and the downscaling trade-offs that come back in M15.
- **Ex:** add a tool whose arguments fail validation and handle the repair loop; measure tokens per call; stream partial structured output.
- **Q:** 8 questions.
- *C++/Rust notes:* tool schemas ≈ an IDL/FFI boundary; validate at the edge like `serde` with `deny_unknown_fields`.

### M3 — The agent loop (5 lessons)
- **L3.1** Perceive → plan → act → observe → reflect: the loop as an event loop with an LLM as the scheduler.
- **L3.2** Building a loop from scratch (~80 lines, no framework): stop conditions, max-steps, error-as-observation.
- **L3.3** The same agent in Pydantic AI, OpenAI Agents SDK, the Vercel AI SDK, and the Claude Agent SDK. What each framework does for you.
- **L3.4** Tool design: granularity, idempotency, error messages written for the model, read vs write tools.
- **L3.5** Failure modes: loops, tool thrash, hallucinated tools, premature "done".
- **WE:** a file-system "explorer" agent (read-only tools) with a step budget.
- **WE (computer-use, preview of M15):** a ~100-line **screenshot → decide → act → observe** loop against a local, network-blocked Playwright page (a fictional form). There's a vendor-neutral action schema with adapters for Anthropic `computer_toolset_20260801` and the OpenAI `computer` tool. CI replays a recorded action script through a mock model, and `--live` uses a real provider. You see the classic failure modes: clicks missed after a layout shift, and the agent declaring "done" without checking.
- **WE (mobile-use):** the same loop on an Android emulator with plain `adb` (`exec-out screencap -p`, `uiautomator dump`, `input tap/text/keyevent`). Compares a screenshot-only observation with an accessibility-tree observation.
- **Ex:** add reflection after failed tool calls; detect and break repetition loops; port the scratch loop to the other language.
- **Q:** 8 questions (including ordering the loop phases and spotting a missing stop condition).
- *C++/Rust notes:* the loop ≈ a `select!`/epoll loop; the step budget ≈ a watchdog timer.
- *Kotlin notes:* ML Kit's on-device `AgentRunner` implements exactly this loop (observe → reason → act → evaluate, `maxTurns`). In M13 we read it as a documented design, then write the same loop ourselves in KMP `commonMain` (Koog) so it runs on the Galaxy A73.

### M4 — Context engineering & memory (5 lessons)
- **L4.1** Context as a scarce resource: what goes in, in what order, and why (instructions, tools, retrieved data, history).
- **L4.2** Short-term memory: conversation compaction, summarisation, tool-result truncation, scratchpads.
- **L4.3** Long-term memory: episodic vs semantic, vector search vs plain files vs structured stores; when *not* to use RAG.
- **L4.4** Retrieval done right: chunking, hybrid search, reranking, and citing sources.
- **L4.5** Progressive disclosure: loading skills and docs on demand (preview of M10).
- **WE:** a repo-QA agent that keeps under a 20k-token budget while answering questions about a 50k-line codebase.
- **WE (GUI & on-device context):** (a) prune an Android accessibility tree / DOM to the interactive nodes and give them stable IDs (set-of-marks), comparing tokens against a full screenshot; (b) downscale screenshots and map model coordinates back to device pixels; (c) fit a useful prompt plus history into a small on-device context budget with summarised memory, using Gemini Nano's documented ~4k-token input limit as the design constraint and a 2,048-token LiteRT-LM context on the A73.
- **Ex:** implement compaction with a fidelity test; add a memory store and an eval that catches stale memory; compare grep-tool vs embedding retrieval on the same questions.
- **Q:** 7 questions.
- *C++/Rust notes:* the context window ≈ a cache with an eviction policy; compaction ≈ log compaction.

### M5 — Planning, reflection, multi-agent & human-in-the-loop (6 lessons)
- **L5.1** Planning patterns: plan-then-execute, ReAct, replanning on new observations.
- **L5.2** Reflection and self-critique: when it helps, when it just burns tokens; verifier models vs deterministic checks.
- **L5.3** Multi-agent patterns: handoffs, agent-as-tool, supervisor/worker, debate. Includes the case *against* multi-agent.
- **L5.4** Human-in-the-loop: approval gates, interrupts and resumes, escalation; avoiding "HITL theater" (Thoughtworks Vol. 35).
- **L5.5** Autonomy as a design choice: mapping your agent onto Feng et al.'s Operator → Observer levels.
- **L5.6** Safety boundaries: sandboxes, least-privilege tools, dry-run modes.
- **WE:** a release-notes agent: the planner writes a plan, workers draft sections, a human approves before publishing (mocked).
- **WE (on-device HITL):** wrap a destructive AppFunction tool (e.g. `delete_recording`) in ML Kit's documented `AgentTool` decorator so it asks the user for confirmation before running. Compare with a LangGraph `interrupt` in Python.
- **WE (GUI-agent safety):** a "consequential action" classifier (submit / pay / send / delete) that forces a human checkpoint in the M3 computer-use loop. Screen text is treated as untrusted input.
- **Ex:** add a replanning trigger; make an approval gate meaningful (show a diff, require a reason); downgrade a 3-agent design to a single agent and compare evals.
- **Q:** 8 questions.
- *C++/Rust notes:* supervisor/worker ≈ actor supervision trees (Erlang/`tokio` tasks with a supervisor).

### M6 — Evals, guardrails, observability, cost & latency (6 lessons)
- **L6.1** Why evals are the unit tests of agents: datasets, graders (exact, programmatic, LLM-as-judge), and regression suites.
- **L6.2** Eval tooling: Inspect AI (Python), promptfoo (TS/CLI), deepeval; running evals in CI with a fixed seed and mock models.
- **L6.3** Trajectory evals: grading tool-call sequences, not just final answers.
- **L6.4** Guardrails: input/output validation, prompt-injection defenses, tool-permission policies, PII handling.
- **L6.5** Observability: OpenTelemetry traces for agent runs (Logfire / Phoenix / LangSmith), and what to log.
- **L6.6** Cost and latency engineering: model routing, caching, parallel tool calls, streaming, budgets and circuit breakers.
- **WE:** an eval suite for the M3 explorer agent: 30 cases, trajectory checks, a cost report.
- **WE (GUI-agent eval harness):** 15 tasks for the M3 computer-use loop. Each task has a **setup → run → state-check → teardown** cycle, in the style of AndroidWorld/OSWorld: the grader inspects the DOM / app database / `adb shell` state, never the agent's own claim. Metrics: success rate, steps, invalid-action rate, unsafe-action attempts, cost, and wall-clock time. Results are seeded and reported as pass@1 and pass@k.
- **WE (on-device eval):** run a golden-prompt suite on the Galaxy A73 across the model ladder (FunctionGemma 270M, Gemma 3 1B, Gemma 4 E2B) and runtimes (LiteRT-LM CPU, llama.cpp CPU, plus LiteRT-LM GPU if it works on the device). Records quality, tool-call accuracy, time to first token (TTFT), tokens/s, and peak memory. The Gemini Nano version-drift variant (`getBaseModelName()`) is shown as a documented case using recorded fixtures.
- **WE (media eval):** objective graders for a media agent: duration and stream checks via `ffprobe`, loudness via ffmpeg's `loudnorm`/`ebur128` filters, and word error rate (WER) for transcripts.
- **Ex:** write an LLM-judge rubric and calibrate it against 10 human labels; add an injection test case that currently passes and fix the agent; set a per-run cost budget that aborts gracefully.
- **Q:** 8 questions.
- *C++/Rust notes:* evals ≈ property tests and fuzzing; traces ≈ `perf`/`tracing` spans; cost budgets ≈ resource quotas.
- *Android notes:* Perfetto/Android Studio profilers for on-device latency and energy, and instrumentation tests as the eval runner on a device.

### M7 — Agent graphs & orchestration (6 lessons)
- **L7.1** From loops to graphs: explicit state machines; when determinism beats autonomy.
- **L7.2** LangGraph in Python and TS: state, nodes, edges, conditional edges, reducers.
- **L7.3** Routers and classifiers: routing by intent, model-tier routing, fallbacks.
- **L7.4** Parallel fan-out / fan-in: map-reduce over documents, `Send`-style dynamic branches, joining partial failures.
- **L7.5** Supervisors and hierarchical graphs: subgraphs, handoffs, shared vs private state.
- **L7.6** Retries, timeouts, checkpoints, and interrupts: resumable graphs and human approval nodes. The same patterns in Mastra workflows.
- **WE:** a document-triage graph: router → parallel extractors → a supervisor merge → a human approval interrupt.
- **WE (GUI-agent graph):** rebuild the M3 computer-use loop as an explicit LangGraph: `observe` (screenshot + a11y tree) → `plan` → `guard` (policy check; `interrupt` for consequential actions) → `act` → `verify` (state diff) → back to `observe` or `recover` / `done`. Includes checkpointing so a crashed emulator run can resume, and a retry policy on `act`.
- **WE (media fan-out graph):** split a video into scenes, then fan out per segment (ASR, frame captioning, OCR) with a concurrency limit, and merge into chapters. This is the core of P7.
- **Ex:** add a retry policy with jitter to a flaky node; convert a free-form agent into a graph and compare evals and cost; implement fan-out with a concurrency limit.
- **Q:** 8 questions.
- *C++/Rust notes:* graph state reducers ≈ CRDT-style merges; fan-out with a limit ≈ a bounded thread pool / `Semaphore`.

### M8 — Durable execution & production agents (5 lessons)
- **L8.1** Why agents need durability: long-running, failure-prone, human-paced work. Workflows vs activities and determinism rules.
- **L8.2** Temporal: workflows and activities in Python and TS; the official OpenAI Agents SDK integration.
- **L8.3** Durable agents with Pydantic AI (Temporal / DBOS) and LangGraph checkpointing. Comparing approaches (Temporal, DBOS, Restate, Inngest).
- **L8.4** Deployment: queues, idempotency keys, secrets, rate limits, multi-tenant isolation.
- **L8.5** Operating agents: SLOs, replay debugging, versioning workflows and prompts, incident runbooks.
- **WE:** kill the worker halfway through a 10-step agent run and watch it resume without repeating side effects.
- **WE (long media jobs):** a Temporal workflow that transcodes and analyses a 2-hour recording in chunks. Activities wrap ffmpeg with idempotent output paths and heartbeats, so a killed worker resumes mid-file.
- **Ex:** make a non-idempotent tool safe; add a signal for human approval that can arrive days later; version a workflow without breaking in-flight runs.
- **Q:** 7 questions.
- *C++/Rust notes:* durable execution ≈ event sourcing plus deterministic replay (like record/replay debuggers such as `rr`).

### M9 — MCP: servers, clients & tool design (6 lessons)
- **L9.1** What MCP standardises (tools, resources, prompts) and what it doesn't. The `2026-07-28` stateless revision explained.
- **L9.2** Building a server in Python (`mcp` 2.x / FastMCP) and TS (`@modelcontextprotocol/server` 2.x): stdio and Streamable HTTP.
- **L9.3** Building clients: connecting an agent framework to MCP servers; `server/discover`; capability negotiation per request.
- **L9.4** Multi Round-Trip Requests (`input_required`), the tasks extension, and caching hints (`ttlMs`, `cacheScope`).
- **L9.5** Security: OAuth (Client ID Metadata Documents), least privilege, tool-poisoning and injection risks, sandboxing servers.
- **L9.6** Testing and debugging: MCP Inspector, contract tests, and migrating v1 → v2 SDKs (the TS codemod).
- **WE:** a "media-probe" MCP server (wraps `ffprobe`: a multimedia-flavoured example for Arunkumar's background) used by an agent.
- **WE (Android tooling over MCP):** use `@mobilenext/mobile-mcp` and `@playwright/mcp` from an agent, then write a minimal **adb MCP server** (`devices`, `screenshot`, `ui_tree`, `tap`, `type`, `logcat_tail`, with destructive commands behind `input_required`). Connect it to Android Studio Agent Mode over **Streamable HTTP** (Studio doesn't support stdio).
- **WE (Kotlin/Rust MCP):** the media-probe server ported to the MCP Kotlin SDK (`0.16.0`, KMP: `commonMain` server, JVM target in CI), plus a **real Rust `rmcp` component**: the `probe`/`loudness` tools implemented in Rust and used by P3. Compared with **AppFunctions** as Android's on-device, OS-mediated equivalent of MCP tools.
- **Ex:** add an `input_required` confirmation step for a destructive tool; add per-tool auth scopes; write contract tests against both spec revisions.
- **Q:** 8 questions.
- *C++/Rust notes:* MCP ≈ LSP for agents (JSON-RPC, capabilities); also how to expose a C++/Rust library as an MCP server through a thin Python/TS layer or a native Rust server.

### M10 — Spec-driven development, rules & skills, agent-friendly repos (6 lessons)
- **L10.1** Spec-driven development: specs as the source of truth. GitHub Spec Kit (`specify`: constitution → spec → plan → tasks → implement) is the **primary** tool used in exercises and projects *(default, confirm in section 7)*; Kiro (requirements → design → tasks) is covered as a side-by-side comparison on the same feature.
- **L10.2** Writing specs that agents can execute: acceptance criteria, non-goals, interfaces, and test oracles.
- **L10.3** Rules files: AGENTS.md (nested), Cursor `.mdc` rules, `CLAUDE.md`. What belongs in them and what doesn't.
- **L10.4** Agent Skills: the `SKILL.md` format, progressive disclosure, scripts inside skills, sharing skills (and skills over MCP).
- **L10.5** Agent-friendly repos: one-command setup, fast deterministic tests, clear module boundaries, typed interfaces, good error messages, a `make verify` target.
- **L10.6** Hooks and guardrails in the dev loop: pre-commit, sandboxed execution, secret scanning, permission allowlists.
- **WE:** take a small Rust or C++ library repo and make it agent-friendly (AGENTS.md + skills + a verify script), then measure the agent's success rate before and after.
- **WE (Android repo):** make an Android app repo agent-friendly: AGENTS.md (read by Android Studio Agent Mode, Claude Code, Codex, and Cursor), Android skills installed via Android CLI (`android skills add`), `./gradlew` verify tasks, and screenshot tests as a fast oracle.
- **Ex:** write a spec with Spec Kit for a small feature and have an agent implement it; write a skill that teaches an agent your team's release process; find three agent-hostile traits in a sample repo.
- **Q:** 8 questions.
- *C++/Rust notes:* AGENTS.md entries for CMake/Cargo builds, sanitizers, and `clippy`/`clang-tidy` as automatic reviewers.

### M11 — Coding & background agents, TDD with agents, review workflows (6 lessons)
- **L11.1** The coding-agent landscape: IDE agents, CLI agents (Claude Code, Codex CLI, Copilot CLI, Gemini CLI), and cloud/background agents (Copilot coding agent, Codex cloud, Cursor cloud agents). How they actually differ.
- **L11.2** TDD with agents: humans write or approve the tests first, the agent makes them pass. Guarding against test tampering.
- **L11.3** Parallel agents: worktrees, task decomposition, avoiding merge conflicts.
- **L11.4** Review workflows: PR size limits, AI pre-review plus human review, review checklists for agent PRs, provenance labels.
- **L11.5** Headless agents in CI: issue → agent → PR pipelines (Claude Agent SDK / Codex / Copilot coding agent), with budgets and kill switches.
- **L11.6** Measuring impact honestly: DORA metrics before and after, rework rate, review latency (ties back to DORA "AI as amplifier").
- **WE:** an issue-to-PR pipeline on a sandbox repo, run through GitHub Actions with a mock agent in CI and a live agent behind a manual trigger.
- **WE (Android agentic dev):** the same feature built three ways: Android Studio Agent Mode (with device tools: deploy, screenshot, Logcat), Claude Code/Codex with the official Android CLI plugin, and a headless agent in CI using `android emulator` + `android run` + `android layout` JSON as a verification oracle. Includes Journeys (natural-language E2E tests, Studio Labs) as an agent-written test layer.
- **Ex:** catch an agent that weakened an assertion; split one oversized agent PR into reviewable stacked PRs; write a review checklist and apply it to three agent PRs.
- **Q:** 8 questions.
- *C++/Rust notes:* agents and UB. Make sanitizers, Miri, and fuzzers part of what "done" means for the agent.

### M12 — Team practice changes by maturity level (4 lessons)
- **L12.1** What changes at each Shapiro level (L0→L5): roles, rituals, review load, and the risk of plateauing at L3.
- **L12.2** DORA's 7 capabilities as entry criteria for each move up; Thoughtworks Vol. 35 cautions (review capacity, HITL theater, cost).
- **L12.3** Governance at team scale: AI policy, data access, tool allowlists, auditability (linked to Microsoft/AWS/Google governance guidance from M1).
- **L12.4** A 90-day adoption plan template with metrics and an exit criterion for each stage.
- **WE:** a fictional 6-person team's journey from L1 to L3, with artifacts at each step (AGENTS.md, eval suite, PR policy).
- **Ex:** critique an adoption plan that skips prerequisites; design the metrics dashboard for a level change.
- **Q:** 6 questions.

### M13 — On-device & Android agents (7 lessons)
- **L13.1** Why (and when not) to run on-device: latency, privacy, offline use, and cost on one side; capability, context size, battery, storage, model download, and device fragmentation on the other. A decision matrix: on-device, cloud, or hybrid.
- **L13.2** *(Documented path, not runnable on the Galaxy A73; exercises use fakes.)* Gemini Nano through ML Kit GenAI / AICore: how to read the supported-device lists and why the A73 isn't on them; the one ML Kit GenAI feature that **does** run on the A73 (speech recognition, Basic mode); task APIs vs the Prompt API (`genai-prompt`); availability checks and model download; documented limits (~4k-token input, foreground-only, per-app quota and battery quota errors, no unlocked bootloaders); model tiers (stable `nano-v2`/`nano-v3`, preview Nano 4 Full/Fast); prompt evaluation across Nano versions. *(Preview-API badge.)*
- **L13.3** On-device tool calling, two ways: **(a) runnable on the A73:** a KMP `commonMain` tool-calling loop (Koog graph strategy) over LiteRT-LM tool use with FunctionGemma 270M / Gemma 3 1B, tools defined once and exposed both to the local model and as MCP tools; **(b) documented, with fakes:** ML Kit `genai-agent` `AgentRunner` + **AppFunctions** tools (`@AppFunctionDeclaration`, KDoc as tool descriptions, `ACCESS_LEVEL_SELF`, scoping with `addAppFunctionIds`, structured error maps, the HITL decorator). AppFunctions as OS-level tools for system agents (Android 16+, experimental), tested with `adb shell cmd app_function`. AppFunctions themselves need Android 16+, so whether the A73 can host them depends on its Android version (to check on the device).
- **L13.4** Hybrid inference: on the A73, Firebase's on-device half isn't available, so the lesson builds **our own router** first (local LiteRT-LM vs the provider-agnostic cloud model) and then shows Firebase AI Logic `PREFER_ON_DEVICE` / `ONLY_ON_DEVICE` / `PREFER_IN_CLOUD` / `ONLY_IN_CLOUD`; what the on-device path does and doesn't support (single-turn, text or text plus one image, structured output); App Check and spend caps on the cloud side; designing your own router (task, privacy class, connectivity, battery).
- **L13.5** Bring-your-own-model runtimes: **LiteRT-LM** (Kotlin `Engine`/`Conversation`, `.litertlm` models from the A73 model ladder, CPU backend first, GPU tried on the device, ABI checks); migrating off the **deprecated MediaPipe LLM Inference API**; **llama.cpp v1.0** (GGUF, `mtmd` multimodal, JNI/NDK builds); **ExecuTorch**; **ONNX Runtime GenAI**; MLC LLM (conceptual only, see unverified list). A comparison table covering formats, accelerators, tool calling, and licensing.
- **L13.6** Quantization & acceleration basics: weights vs activations vs KV cache; int8/int4/FP8; per-channel/group scales; GGUF quant types and `llama-quantize`; `torchao`/LiteRT Torch export; how much quality you lose, measured (perplexity plus task evals). Accelerators: CPU, GPU, and NPU, using the A73 as a worked example of reading vendor support tables (2.3.1): LiteRT and ExecuTorch NPU support **excludes** the 778G, while the chip has a Hexagon V68 HTP. **Experimental stretch:** run a small quantized ONNX model (e.g. an image classifier, not an LLM) through the ORT QNN EP's HTP backend on the A73, compiling the context on the device. Clearly labelled "may not work". LiteRT `CompiledModel` NPU paths (Qualcomm AI Engine Direct, MediaTek NeuroPilot, Google Tensor AOT) and Google Play for On-device AI delivery are covered conceptually.
- **L13.7** Measuring and shipping: TTFT, tokens/s, peak RSS, thermal throttling, energy (Perfetto, Android Studio profilers); device-tier test matrices (JVM + emulator for logic; the **Galaxy A73** as the physical reference device for CPU/GPU numbers; Android Device Streaming if someone wants to try the Gemini Nano path on a supported device); measuring the A73's real RAM headroom per model; privacy review (what leaves the device, logging, retention).
- **WE:** an **offline "voice notes" assistant that runs on the Galaxy A73**. KMP: the agent loop, tool schemas (`search_notes`, `create_note`, `delete_note`; the last is HITL-gated) and evals live in `commonMain`; `androidMain` has three interchangeable backends: **LiteRT-LM** (CPU; primary), **llama.cpp** via NDK/JNI (CPU, GGUF Q4), and **ExecuTorch** (XNNPACK, CPU). Voice input uses ML Kit GenAI speech recognition in **Basic** mode (supported on the A73). Long summaries go to a provider-agnostic cloud model behind an explicit privacy check. The same `commonMain` agent runs on the JVM in CI with a fake model. A **documented Gemini Nano + `AgentRunner` + AppFunctions** flavour compiles and passes its tests against fakes, with a note that it needs a supported device. Ends with a benchmark table measured on the A73.
- **Ex:** (1) add an availability/feature-check state machine with good UX for "model downloading" or "unsupported device", tested against the A73's real answers (Nano unavailable, speech Basic available); (2) quantize a small model to Q4 and Q8 with llama.cpp, then chart quality vs speed vs size; (3) write a router that keeps PII-tagged prompts on-device; (4) migrate a MediaPipe `LlmInference` sample to LiteRT-LM.
- **Q:** 9 questions (e.g. "Why does this call return `BACKGROUND_USE_BLOCKED`?", "Which quantization change shrinks the KV cache?").
- *Kotlin notes:* KMP layout (`commonMain` agent + `expect`/`actual` or interface-injected backends), one single-thread owner for native engines, structured concurrency, `Flow` for token streams, `AutoCloseable` lifecycles tied to `ViewModel`/`Lifecycle`.
- *C++/Rust notes:* llama.cpp/whisper.cpp through the NDK + JNI; ABI splits (`arm64-v8a`, `x86_64`); exposing a Rust inference core to Kotlin through a C ABI; memory-mapped weights and page-cache behaviour on Android.

### M14 — Multimedia & multimodal agents (6 lessons)
- **L14.1** Multimodal models for media: image, audio, and video inputs; frame sampling strategies; token and cost accounting per frame or second; on-device (Gemma 4 E2B/E4B via LiteRT-LM, with video as sampled frames) vs cloud multimodal models.
- **L14.2** Agents driving **ffmpeg** safely: typed tool wrappers (never raw shell strings); `ffprobe -print_format json` as the observation; key filters for agents (`select`/scene scores, `silencedetect`, `loudnorm`/`ebur128`, `thumbnail`, `concat`); dry-run and verify-output patterns; PyAV for frame-accurate work.
- **L14.3** **GStreamer** pipelines as tools: the agent proposes a pipeline description, a validator parses it and checks it against an element allowlist, and it runs in a sandbox with timeouts. GStreamer 1.28 ML inference elements (`onnxinference` → `tensordecodebin`) for inline detection; PyGObject control (bus messages as observations). Android equivalents: Media3 Transformer / ExoPlayer and CameraX analysers.
- **L14.4** Speech & audio agents: VAD (silero-vad) → ASR (whisper.cpp / faster-whisper) → diarization (pyannote.audio) → LLM post-processing; streaming vs batch latency budgets; ML Kit GenAI speech recognition (alpha) on Android.
- **L14.5** Vision & video understanding pipelines: shot/scene detection (PySceneDetect / ffmpeg), keyframe selection, MediaPipe Tasks (vision/audio) for cheap detectors before expensive VLM calls, OCR, captioning; "cheap filter first, VLM second" for cost and latency.
- **L14.6** Evaluating media agents: golden fixtures (short CC-licensed clips checked into `media-fixtures/`), objective metrics (duration/stream invariants, LUFS, WER, frame-accurate cut points), LLM-judge rubrics for captions and summaries, and privacy handling for faces, voices, and screen recordings.
- **WE:** a **"highlight reel" agent**: probe → scene detect → transcribe → score segments (multimodal model) → plan an edit decision list → ffmpeg concat with loudness normalisation → verify against the plan with `ffprobe`. Python and TS versions; mock models in CI with fixed transcripts and frame captions.
- **Ex:** (1) add a GStreamer live-camera path with `onnxinference` doing person detection and an agent that starts or stops recording; (2) build an argument allowlist that blocks `-f` and protocol tricks (`concat:`, `http:`) in ffmpeg tool calls; (3) measure the WER and latency trade-off between whisper.cpp model sizes; (4) port the probe tool to Kotlin with the platform `MediaExtractor` / `MediaMetadataRetriever` APIs.
- **Q:** 8 questions.
- *C++/Rust notes:* writing a custom GStreamer element (C or the Rust bindings) that emits analytics metadata for an agent to consume; zero-copy buffers and why agents should operate on metadata, not raw frames.
- *Kotlin notes:* Media3 Transformer for on-device edits driven by an on-device agent; foreground-service constraints vs ML Kit's foreground-only inference rule.

### M15 — Computer-use & mobile-use agents (6 lessons)
- **L15.1** GUI agents from first principles: observation spaces (pixels, accessibility tree/DOM, annotated screenshots, app APIs) and action spaces (coordinates, element IDs, intents/AppFunctions). The rule: **use an API, MCP tool, or AppFunction when one exists; use GUI automation only when it doesn't.**
- **L15.2** Computer-use APIs in practice: Anthropic `computer_toolset_20260801` (client-executed member tools, batched actions, `browser_toolset_20260801`) and the OpenAI Responses `computer` tool (`computer_call` actions → `computer_call_output` screenshots) plus its code-execution variant and SDK toolsets with `before_action`/`confirm` hooks. Playwright, browser-use, and Playwright MCP for the web. Sandboxes: Docker + Xvfb desktop, E2B Desktop, cua.
- **L15.3** Mobile-use: `adb` primitives (screencap, `uiautomator dump`, `input`, `am`/`pm`), UI Automator and `AccessibilityNodeInfo`, `uiautomator2` (Python), Android CLI `screen capture --annotate` and `android layout` JSON, the mobile-mcp server, frameworks such as DroidRun and minitap mobile-use (compared, not depended on), and emulator snapshots for repeatable starts.
- **L15.4** Reliability engineering: grounding (set-of-marks, element IDs over raw coordinates), coordinate scaling, waiting for idle, verify-after-act, recovery strategies (back, home, relaunch), step and time budgets, and deterministic replays for debugging.
- **L15.5** Safety: screen content is untrusted (prompt injection in pages, notifications, and emails); action and domain allowlists; human confirmation for consequential actions (purchases, sends, deletes, typing sensitive data); fresh profiles/VMs; credentials never shown on screen; network egress rules; audit logs of screenshots and actions; Thoughtworks Vol. 35 "agent sandboxing" and the risk of HITL theater.
- **L15.6** Benchmarks & your own evals: AndroidWorld (116 tasks, 20 apps, state-based rewards, Pixel 6 / API 33 AVD), OSWorld / OSWorld-Verified (Ubuntu desktop, execution-based checks), and WebArena (self-hosted web apps). Why public leaderboards are self-reported and quickly saturate. Building a private mini-benchmark with task templates, randomised parameters, state checkers, and pass@k.
- **WE:** the same task ("create a calendar event from an email") solved three ways and compared on the M6 harness: (a) a pure computer-use loop, (b) a hybrid that uses the accessibility tree plus screenshots, and (c) an API/AppFunction call. The comparison shows why (c) wins whenever it's available.
- **Ex:** (1) add set-of-marks annotation and measure the change in invalid-action rate; (2) write a prompt-injection fixture (a notification saying "ignore previous instructions…") and make the guard catch it; (3) run 5 AndroidWorld tasks with your agent and report pass@1 with the step budget stated; (4) turn a recorded successful trajectory into a deterministic regression test.
- **Q:** 8 questions.
- *C++/Rust/Kotlin notes:* a tiny Kotlin AccessibilityService or UI Automator helper that streams a compact UI tree over a local socket (faster than `uiautomator dump`); using the emulator's gRPC endpoint (`-grpc`) for fast screenshots from a Rust/C++ harness.

---

## 4. Exercises, solutions & quizzes: conventions
- Each exercise has a **starter** (`exercises/mX/exY/starter`), a **test file** (what "done" means), and a **solution** (`exercises/mX/exY/solution`). CI runs the tests against the solution and checks that the starter **fails** them, so exercises can't go stale.
- Exercises that involve LLM judgement use rubric-based evals with mock graders in CI and an optional live grader.
- Quizzes are YAML files (`quizzes/mX.yaml`) with a question, choices, the answer, and an explanation, validated by a JSON Schema in CI.

---

## 5. End-to-end projects

Each project has a spec (written Spec Kit-style), milestones, an eval suite, a reference solution (hidden), and a rubric.

**P1 — "Mini-SWE": a coding agent that plans, edits, tests, and opens a PR** (after M3–M6, M10–M11)
- Takes a GitHub issue → writes a plan → edits files with read/write/search tools in a sandbox (container/worktree) → runs tests → iterates → opens a PR with a summary and a test report.
- Concepts: agent loop, tool design, context engineering on a repo, TDD with agents, guardrails (path allowlist, no network), evals on a fixed benchmark of 15 seeded bugs, cost budget.
- Variants: Python with Pydantic AI or the Claude Agent SDK; TS with the AI SDK. Stretch: run it as a background agent from GitHub Actions on a sandbox repo.

**P2 — Graph research agent with supervisor + evals** (after M5–M7)
- A LangGraph (Py or TS) supervisor routes sub-questions to parallel researcher workers (fan-out), a critic node checks citations, and a human interrupt approves the final report.
- Concepts: routers, fan-out/fan-in, supervisor, reflection, retries, checkpoints, a trajectory + factuality eval suite, tracing with OTel, cost/latency report.

**P3 — Media MCP server + agent that uses it** (after M9; the extended version after M14)
- **Core:** an MCP server `media-toolkit` in **both** Py and TS on spec `2026-07-28`. Tools: `probe` (ffprobe JSON), `detect_scenes`, `detect_silence`, `measure_loudness`, `extract_frames`, `transcode` (preset allowlist), `cut`/`concat` (from an edit decision list). Destructive or expensive operations go through `input_required` confirmation; long jobs use the tasks extension with progress; OAuth on the Streamable HTTP transport; contract tests on golden media fixtures. Then an agent client that uses it, plus an eval suite (objective checks via `ffprobe`/loudness/duration).
- **Extended (after M14):** add GStreamer tools: `validate_pipeline` (parse + element allowlist), `run_pipeline` (sandboxed, with a timeout), and `live_detect` (1.28 `onnxinference` → `tensordecodebin` → events as MCP notifications on the request stream). Add a **Kotlin** port with the MCP Kotlin SDK (`0.16.0`) that exposes Android-side media tools through adb (`screenrecord`, pulling files from a device, Media3 Transformer jobs triggered by intent). Connect the server to Android Studio Agent Mode over HTTP.
- Concepts: MCP server/client, tool design for dangerous CLIs, security, MRTR, tasks, evals, packaging. **Rust component (required, default):** the `probe` and `loudness` tools ship as a Rust `rmcp` (`3.10.0`) server that the Python/TS client calls, with the same contract tests as the Python server. Stretch: a custom GStreamer element (Rust or C) whose analytics metadata appears as a resource.

**P4 — Durable triage & remediation workflow** (after M7–M8)
- Takes an incident/bug report → classify → gather logs (tools) → propose a fix → human approval (a signal that may come days later) → apply the change and verify. Runs on Temporal (Py or TS) and survives worker kills.
- Concepts: durable execution, idempotent tools, HITL, versioning, observability, SLOs.

**P5 — Capstone: move a small team project up one maturity level** (after M10–M12)
- Start from a provided "legacy" multi-module repo (Python + TS + a small Rust crate) at roughly Shapiro L1. Do a baseline assessment with the M1 worksheet and DORA capabilities → make it agent-friendly (AGENTS.md, skills, verify script, fast tests) → introduce spec-driven flow → set up an agent PR pipeline with review policy → measure before and after (agent task success rate on 10 seeded tasks, review time, rework).
- Deliverables: an assessment report, repo changes, an adoption plan, a metrics dashboard, and a retrospective.

**P6 — On-device Android agent app with tool calling** (after M13; Kotlin)
- A Compose app, "Field Notes": an offline assistant that searches, creates, tags, and summarises notes and voice memos on-device.
- **Primary path (runs on the Galaxy A73):** a KMP app. `commonMain` holds a Koog agent (graph strategy, tools, HITL on `delete_*`/`share_*`, persistence so sessions survive configuration changes and process death). `androidMain` uses **LiteRT-LM on CPU** with the A73 model ladder (FunctionGemma 270M for tool routing, Gemma 3 1B / Gemma 4 E2B for answers) and ML Kit GenAI speech recognition (Basic mode) for voice memos. The JVM target runs the same agent in CI. **GPU:** a LiteRT-LM GPU option, enabled only if it passes the on-device test on the A73. **Cloud fallback:** a provider-agnostic cloud model for long summaries, behind a privacy router.
- **Documented flavour (built, tested with fakes):** Gemini Nano via ML Kit `genai-agent` `AgentRunner` with **AppFunctions** tools (`ACCESS_LEVEL_SELF`, scoped IDs, HITL decorator) and Firebase AI Logic `PREFER_ON_DEVICE`. On the A73 this flavour detects that Nano is unavailable and shows the documented fallback.
- **Evals:** a golden-prompt and tool-trajectory suite that runs as instrumentation tests on the **Galaxy A73** (self-hosted, via `adb`); a JVM-level suite with a fake model for CI; a performance report (TTFT, tokens/s, energy via Perfetto) per backend; a privacy checklist (no network on the on-device path, verified by a test with network disabled).
- Concepts: on-device inference, tool calling, HITL, hybrid routing, quantized models, evals, latency/power/privacy trade-offs. C++ stretch: a llama.cpp (NDK/JNI, CPU) backend behind the same Kotlin interface. NPU stretch (experimental, may fail): ORT QNN EP HTP for a small quantized helper model.

**P7 — Multimodal media-analysis agent graph** (after M7, M14)
- A LangGraph (Py; TS port optional) that ingests a long recording (a talk, a meeting, or a screen recording) → `probe` → `segment` (scene + silence) → **parallel fan-out** per segment: ASR (whisper.cpp / faster-whisper), keyframe captioning + OCR (VLM, cheap MediaPipe/ONNX filters first), audio events → a **supervisor** that merges the results into chapters, a summary, a searchable index, and an optional highlight reel (ffmpeg via the P3 MCP server) → a **verify** node (timestamps monotonic, cut points within tolerance, loudness target met) → a human-approval `interrupt` before publishing.
- **Local vs cloud switch:** an entirely local profile (llama.cpp `mtmd` multimodal model + whisper.cpp) vs a cloud profile, with the cost, latency, and quality comparison recorded.
- **Evals:** 10 golden fixtures with reference chapters and transcripts; WER, chapter boundary F1, LLM-judge on summaries, cost per media hour. Durable variant on Temporal for multi-hour files.
- Concepts: multimodal models, graphs (fan-out/fan-in, supervisor, retries, checkpoints), media tooling, evals, cost/latency.

**P8 — Mobile/computer-use agent as a graph, with safety checkpoints and an eval harness** (after M6, M7, M15)
- A LangGraph agent with explicit nodes: `observe` (screenshot + pruned accessibility tree / DOM, set-of-marks annotation) → `plan` (subgoal + next action) → `guard` (policy engine: action/domain allowlists, consequential-action detector, injection heuristics; `interrupt` for human approval) → `act` (adapters: **adb/uiautomator2** for Android, **Playwright** for web) → `verify` (state diff, expected-screen check) → `recover` or loop. Checkpointed so a crashed emulator run can resume. Step, time, and cost budgets are enforced by the graph, not the prompt.
- **Model adapters (all three ship):** (1) **Anthropic** `computer_toolset_20260801` (client-executed tools, batched actions); (2) **OpenAI** Responses `computer` tool (`computer_call` → `computer_call_output`, with `before_action`/confirm hooks mapped onto the `guard` node); (3) a **vendor-neutral reference**: the graph's own JSON action schema + set-of-marks IDs, driven by any vision-capable model via the provider-agnostic `COURSE_LLM_*` config. All three map into one internal action type, so the guard, verify and eval code is shared, and the harness reports results per adapter. Vendor-specific model names aren't pinned.
- **Environments:** an Android emulator (Pixel 6 / API 33 image, matching AndroidWorld) with snapshots, and a local sandboxed web app in Docker with no outbound network.
- **Eval harness:** 20 custom tasks (10 mobile, 10 web) with setup/teardown and **state-based checkers** (app DB / `adb shell content query` / DOM), plus an opt-in subset of AndroidWorld tasks. Metrics: success (pass@1, pass@3), steps, invalid actions, unsafe-action attempts blocked, human interventions, cost, and time. CI runs the harness against a **mock model that replays recorded trajectories** (deterministic), and a nightly or manual job runs live models (each adapter) on the self-hosted KVM runner. An optional run on the physical Galaxy A73 covers real-device quirks.
- **Deliverables:** the graph, the harness, a failure-taxonomy report (grounding, planning, verification, safety), and an ablation (screenshot-only vs a11y tree vs both).
- Concepts: agent loop, graphs, HITL, guardrails, evals, durable/checkpointed execution, mobile tooling. **Rust component:** a small Rust helper that grabs screenshots from the emulator's gRPC endpoint and diffs frames for the `verify` node (Python fallback included). Kotlin stretch: a companion AccessibilityService that streams a compact UI tree; adding AppFunction calls as "API-first" actions and measuring the improvement.

---

## 6. Site outline

### 6.1 Static site generator: **Astro Starlight** (recommended)
- **Why Starlight (`@astrojs/starlight 0.42.11` on `astro 7.4.11`):**
  - MDX + components make interactive quizzes and collapsible solutions straightforward (Astro islands; no backend).
  - Python/TS code tabs (`<Tabs syncKey="lang">`) stay in sync across the whole site.
  - Built-in search (Pagefind), dark mode, i18n, sidebar autogeneration, and Expressive Code for highlighting and diffs.
  - Code shown on pages can be **imported straight from the tested example files** (`import code from '../../examples/m3/loop.py?raw'`), so the code readers see is the code CI tested.
  - `starlight-links-validator` fails the build on broken internal links.
- **Why not MkDocs Material:** an excellent tool, but the maintainers have put Material for MkDocs into **maintenance mode, with end of life extended to 5 May 2027** (https://github.com/squidfunk/mkdocs-material/issues/8523), and are moving to Zensical. Building a new course on it now would mean a migration within about 6 months. Zensical is worth watching but is still reaching feature parity.

### 6.2 Repo layout (proposed: `pragmaticarun/ai-native-course`)
```
ai-native-course/
├─ site/                      # Astro Starlight
│  ├─ astro.config.mjs
│  └─ src/
│     ├─ content/docs/
│     │  ├─ index.mdx         # landing
│     │  ├─ start/            # M0
│     │  ├─ maturity/         # M1
│     │  ├─ fundamentals/     # M2–M6
│     │  ├─ orchestration/    # M7–M8
│     │  ├─ ai-native/        # M9–M12
│     │  ├─ on-device-media/  # M13–M14
│     │  ├─ gui-agents/       # M15
│     │  ├─ projects/         # P1–P8
│     │  ├─ reference/        # glossary, versions, sources, cheat-sheets
│     │  └─ changelog.mdx
│     └─ components/          # Quiz.astro, Solution.astro, LangTabs, VersionBadge, MaturityRadar
├─ examples/{python,ts}/mXX/  # every snippet shown on the site
├─ kmp/                       # Kotlin Multiplatform: shared/commonMain (agents, tools, MCP), jvmMain (CI), androidMain (backends)
├─ rust/                      # rmcp media server (P3), emulator screenshot/diff helper (P8)
├─ android/                   # Gradle app module for M13/P6 consuming kmp/shared (libs.versions.toml)
├─ media-fixtures/            # small CC-licensed clips + reference transcripts/chapters (Git LFS)
├─ envs/                      # Dockerfiles: media (FFmpeg 9.0.2, GStreamer 1.28.9), cua-web sandbox, emulator helpers
├─ exercises/mXX/exYY/{starter,solution,tests}
├─ projects/pN/{spec,starter,solution,evals}
├─ quizzes/mXX.yaml
├─ python/ (pyproject.toml, uv.lock)   ts/ (package.json, pnpm-lock.yaml)
├─ AGENTS.md  .cursor/rules/  .claude/skills/   # the course practices what it teaches
├─ CHANGELOG.md  renovate.json
└─ .github/workflows/{ci.yml,deploy.yml,live-nightly.yml,link-check.yml}
```

### 6.3 Page structure (every lesson page)
1. Title, time estimate, prerequisites, "versions used" badge (generated from the lockfiles).
2. **Intuition** (diagram + analogy) → 3. **Minimal example** (Py/TS tabs) → 4. **Try it** (guided changes) → 5. **C++/Rust/Kotlin notes** callout → 6. **Exercises** (each with a collapsed `<Solution>`) → 7. **Sources** (links to primary docs) → 8. Prev/next navigation. Module index pages end with the **quiz**.

### 6.4 Navigation
Top level: *Start here · Maturity · Agent Fundamentals · Orchestration · AI-Native Programming · Projects · Reference · Changelog*. The left sidebar is generated per section with module → lessons. A global language toggle (Python / TypeScript, plus Kotlin where available) is remembered in localStorage. Lessons on alpha/beta platform APIs show a **"preview API"** badge, and lessons that need specific hardware show a **"device required"** badge (e.g. AICore-capable phone, NPU). "Learning paths" on the landing page: *Agent builder* (M2–M8, P2, P4), *AI-native engineer* (M9–M11, P1, P3), *Team lead* (M1, M10, M12, P5), *Android & on-device engineer* (M2–M4, M6, M13, M9, P6, P3-extended), *Media agents* (M7, M14, P3, P7), *GUI agents* (M3, M6, M7, M15, P8). New top-level nav items: **On-device & Media** and **GUI Agents**.

### 6.5 How hidden solutions work
- `<Solution>` is a `<details>` element styled as "Show solution". The body is imported from `exercises/.../solution` (tested code) plus an explanation. Optionally it reveals step by step ("Hint 1 → Hint 2 → Full solution").
- **Honest caveat:** on a public static site, "hidden" means *collapsed*, not secret; the solutions are in the page source and the repo. If real secrecy is ever needed (e.g. for graded cohorts), keep solutions in a separate private repo and build two variants. Not proposed for v1.

### 6.6 How quizzes work
- `<Quiz src="m3" />` reads `quizzes/m3.yaml` at build time. The questions render as an Astro island with client-side checking, per-question explanations, a score, and progress saved in localStorage only (no tracking, no backend).
- Question types: single/multi choice, ordering (e.g. the agent-loop phases), "spot the bug" (pick the line in a code block).
- CI validates the YAML against a schema and checks that every answer key exists.

### 6.7 Changelog page
- `CHANGELOG.md` (Keep-a-Changelog format) is rendered at `/changelog/`, with sections for **Content**, **Dependency bumps** (from Renovate PRs, with old → new versions), **Spec changes** (e.g. MCP revisions), and **Errata**.
- `/reference/versions/` is generated from the lockfiles at build time, so the pinned versions shown always match what CI tested. Each page shows a "last verified" date.

### 6.8 CI that runs every code example
- **`ci.yml`** (on PRs and pushes to main):
  1. `python`: `uv sync --locked` → `ruff` → `mypy` → `pytest examples/python exercises projects` (mock models; no network; Python 3.13 & 3.14 matrix).
  2. `ts`: `pnpm install --frozen-lockfile` → `tsc --noEmit` → `vitest run` (mock providers).
  3. `exercises`: solutions must pass and starters must fail their tests.
  4. `evals`: Inspect AI / promptfoo suites in mock mode, with fixed thresholds.
  5. `services`: Temporal dev server and Postgres as service containers for the M8/P4 tests.
  6. `kmp-android`: `./gradlew :kmp:shared:jvmTest :android:assembleDebug :android:testDebugUnitTest lint`. Model calls go through an interface with a fake (including recorded Gemini Nano responses/errors for the documented flavour); no AICore or device in CI.
   6b. `rust`: `cargo fmt --check`, `cargo clippy -D warnings`, `cargo test` for `rust/` (P3 server contract tests, P8 helper).
  7. `media`: in the `envs/media` container (FFmpeg 9.0.2, GStreamer 1.28.9), run M14/P3/P7 examples on `media-fixtures/` with mock model outputs and objective checks (ffprobe, loudness, WER on fixed transcripts).
  8. `cua`: headless Playwright against the local sandbox web app, with the GUI-agent graph replaying recorded trajectories through a mock model (deterministic). Mobile trajectories are replayed against recorded screenshots and UI-tree fixtures, so no emulator is needed here.
  9. `site`: `astro build` + `starlight-links-validator` + quiz schema validation + a check that every `?raw` import points to a tested file.
- **`link-check.yml`** (weekly): an external link checker (e.g. lychee) over all source links. It opens an issue rather than failing deploys, because some publishers (Gartner, BCG, McKinsey) block bots.
- **`live-nightly.yml`** (scheduled + manual): runs a small curated set of examples against real providers using repository secrets and a hard spend cap. It reports drift without blocking anything.
- **`device-lab.yml`** (manual / nightly, non-blocking): (a) an Android emulator job for M15/P8 live runs and the AndroidWorld subset on a **self-hosted Linux runner with KVM** (agreed), labelled e.g. `[self-hosted, linux, kvm]`; (b) an instrumentation-test + benchmark job for M13/P6 on the **Galaxy A73** attached by USB/`adb` to a self-hosted runner. GPU/NPU and performance results are published as reports, never as gates. Because these runners execute workflow code, they're only triggered manually or on `main`, never from fork PRs.
- **`deploy.yml`**: on main, build with `withastro/action` and deploy with `actions/deploy-pages` to GitHub Pages (`site: https://pragmaticarun.github.io`, `base: /ai-native-course`).
- **Renovate**: grouped weekly PRs for dependency bumps; an automerge-free policy, with every bump adding a changelog entry.

---

## 7. Open questions for Arunkumar
**Defaults now applied (confirm or override):**
1. **Live provider: default = provider-agnostic.** `--live` and the nightly job read `COURSE_LLM_PROVIDER` / `COURSE_LLM_MODEL` + that provider's key. Still open: which provider(s) to use for the nightly job, and whether any API keys should be stored as repo secrets at all.
2. **P3: default = the ffmpeg/GStreamer media MCP toolkit** (no generic alternative).
3. **Rust: default = some real Rust components** (P3 `rmcp` server tools, P8 emulator screenshot/diff helper, the P5 legacy crate), with everything else as notes and stretches.
4. **Spec-driven: default = Spec Kit primary, with a Kiro comparison.**

**Still open:**

5. Public repo from day one, or private until M0–M3 are done? (If public, the self-hosted KVM/A73 runners must never run fork-PR workflows; 6.8 already assumes this.)
6. Which Android/One UI version is your A73 on now? It decides whether AppFunctions (Android 16+) can be demonstrated on your phone. Is it the 6 GB or 8 GB variant? That decides whether Gemma 4 E2B is in the A73 model ladder or stops at Gemma 3 1B.
7. Is it OK to keep the A73 attached to the self-hosted runner for nightly benchmark/instrumentation jobs, or should that job be manual-only?

## 8. Could not verify / deliberately left out
- **Galaxy A73 items (v0.3):**
  - **LiteRT-LM GPU on the Adreno 642L:** not verified (no published result for the 778G). Treated as "try on the device".
  - **ORT QNN EP HTP on the 778G (V68):** plausible from ORT's SM8350 testing and Qualcomm's table, but not verified on this chip; there's a reported host-compiled V68 context-binary failure. Experimental stretch only.
  - **SNPE/QAIRT direct use** on the A73: the Qualcomm table lists HTP V68 support, but we haven't checked SDK licence and download terms for course use. Not used.
  - **Firebase AI Logic fallback behaviour on an unsupported device:** inferred (cloud path), not tested.
  - **A73's current Android/One UI version and RAM variant:** not known (asked in section 7). AppFunctions need Android 16+.
  - **Gemma 4 E2B on 6 GB / 8 GB:** the only published memory figure is from the S26 Ultra (~1.7 GB peak CPU memory, 2.58 GB file). Fit on the A73 to be measured.
  - **MCP Kotlin SDK on Android:** the SDK targets JVM/Native/JS/Wasm (no Android-specific artifact); using the JVM artifact on Android is assumed, not tested.
  - **llama.cpp on the A73's CPU:** CPU builds for Android are documented generically; no A73-specific result. OpenCL on the Adreno 642L isn't on the verified list, so it's not used.
- **Android / on-device / media / GUI-agent items (v0.2):**
  - **Gemini Nano on emulators:** not verified. We assume AICore paths need a supported physical device (the A73 isn't one), and CI uses fakes.
  - **`genai-agent 1.0.0-alpha1` + AppFunctions:** ML Kit docs pair it with `appfunctions 1.0.0-alpha13`, but `1.0.0-rc01` is on Google Maven. Compatibility with rc01 hasn't been tested, so the course pins alpha13.
  - **ML Kit Prompt API version:** the docs show `genai-prompt 1.0.0-beta4`, while Google Maven has `1.0.0-beta5`. We pinned beta5 without testing it.
  - **`llama-cpp-python 0.3.36`** (1 Oct 2026) predates **llama.cpp v1.0.0** (13 Nov 2026), which removed deprecated APIs. Whether the binding works with v1.0.0 is unknown, so pin a llama.cpp build the binding supports, or call llama.cpp's server/CLI.
  - **`ai-edge-torch` → `litert-torch` rename:** inferred from matching version numbers and the docs' "LiteRT Torch" naming. Not confirmed by an announcement.
  - **MLC LLM:** no current release or version found (no stable GitHub release, no PyPI package). Covered conceptually only.
  - **ONNX Runtime GenAI for Android:** no Maven Central artifact found. How it's distributed for Android isn't verified.
  - **ExecuTorch:** the Android Maven artifact (1.5.1) lags the 1.6.0 release. We pinned 1.5.1 for Android.
  - **minitap `mobile-use`:** PyPI `minitap-mobile-use 4.0.0` (Aug 2026) doesn't match GitHub's latest release `v3.3.0`, and the older `mobile-use` PyPI name is stale. Treated as "compare only".
  - **DroidRun:** the PyPI package has no repository link in its metadata (the GitHub release v0.7.4 matches the version).
  - **Benchmark leaderboards** (AndroidWorld, OSWorld-Verified): scores are mostly self-reported or from aggregators, so the course won't quote them.
  - **WebArena:** the repo's last tagged release is from 2023. Newer "verified" variants weren't checked.
  - **Gemma 4 model file sizes** and the claim that LiteRT-LM lacks native video input come from search summaries and secondary sources, so they're not quoted as facts. The course says "video as sampled frames" as a design choice.
  - **KVM on GitHub-hosted runners** (for emulators): not verified, and no longer needed (a self-hosted KVM runner is agreed).
  - **Vendor model names** in docs (e.g. in the OpenAI/Anthropic computer-use examples) were seen, but the course stays model-agnostic and doesn't pin them.
  - **Android Studio:** we didn't record a current Android Studio release number (we used feature docs, not a version).
- The **original Gartner document** for the Awareness → Transformational levels (paywalled); cited only through secondary sources and labelled as such.
- **BCG's emerging/stagnating split** of the 60% laggards: seen only in search summaries, not on the BCG page we fetched.
- **Accenture archetype percentages** and **Deloitte statistics**: not quoted, because we didn't read those figures in the source text.
- **McKinsey "State of AI in 2026"** (reportedly Aug 2026 PDF): found via search, but the PDF didn't load from our tools, so it isn't cited and the 2025 edition is used instead.
- **Google Jules shutdown** claim: from a third-party ranking only. Not stated as fact.
- **PyPI `specify-cli` provenance**: its version matches Spec Kit v1.4.0, but there's no repo link in its metadata. We recommend installing from GitHub.
- **Deloitte 2025 "autonomous agents" statistics** and any "Level 0–5 AI coding" scales other than Shapiro's: excluded, because we found no single authoritative source.
- No published "official" levels from GitHub (Octoverse) or OpenAI/Anthropic for AI-coding autonomy were found, so none are claimed.
