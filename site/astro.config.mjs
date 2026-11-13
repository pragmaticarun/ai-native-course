// @ts-check
import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";
import starlightLinksValidator from "starlight-links-validator";

export default defineConfig({
  site: "https://pragmaticarun.github.io",
  base: "/ai-native-course",
  integrations: [
    starlight({
      title: "AI-Native Software Development",
      description:
        "Maturity models, agent loops, graphs, MCP, on-device & GUI agents, for experienced systems engineers.",
      social: [{ icon: "github", label: "GitHub", href: "https://github.com/pragmaticarun/ai-native-course" }],
      editLink: { baseUrl: "https://github.com/pragmaticarun/ai-native-course/edit/main/site/" },
      lastUpdated: true,
      customCss: ["./src/styles/custom.css"],
      plugins: [starlightLinksValidator()],
      sidebar: [
        { label: "Start here (M0)", items: [{ autogenerate: { directory: "start" } }] },
        { label: "Maturity (M1)", items: [{ autogenerate: { directory: "maturity" } }] },
        {
          label: "Agent Fundamentals",
          items: [
            { label: "M2 · LLM & tool calling", items: [{ autogenerate: { directory: "fundamentals/m2" } }] },
            { label: "M3 · The agent loop", items: [{ autogenerate: { directory: "fundamentals/m3" } }] },
            { label: "M4 · Context & memory", items: [{ autogenerate: { directory: "fundamentals/m4" } }] },
            { label: "M5 · Planning, multi-agent & HITL", items: [{ autogenerate: { directory: "fundamentals/m5" } }] },
            { label: "M6 · Evals, guardrails & cost", items: [{ autogenerate: { directory: "fundamentals/m6" } }] },
          ],
        },
        {
          label: "Orchestration & Production",
          items: [
            { label: "M7 · Agent graphs & orchestration", items: [{ autogenerate: { directory: "orchestration/m7" } }] },
            { label: "M8 · Durable execution & production", items: [{ autogenerate: { directory: "orchestration/m8" } }] },
          ],
        },
        {
          label: "AI-Native Development",
          items: [
            { label: "M9 · MCP servers & clients", items: [{ autogenerate: { directory: "ai-native/m9" } }] },
            { label: "M10 · Specs, rules & skills", items: [{ autogenerate: { directory: "ai-native/m10" } }] },
            { label: "M11 · Coding agents & review", items: [{ autogenerate: { directory: "ai-native/m11" } }] },
            { label: "M12 · Team practice by level", items: [{ autogenerate: { directory: "ai-native/m12" } }] },
          ],
        },
        {
          label: "On-device & Media",
          items: [
            { label: "M13 · On-device & Android agents", items: [{ autogenerate: { directory: "on-device-media/m13" } }] },
            { label: "M14 · Multimedia & multimodal agents", items: [{ autogenerate: { directory: "on-device-media/m14" } }] },
          ],
        },
        {
          label: "GUI Agents",
          items: [{ label: "M15 · Computer-use & mobile-use agents", items: [{ autogenerate: { directory: "gui-agents/m15" } }] }],
        },
        { label: "Projects", items: [{ autogenerate: { directory: "projects" } }] },
        { label: "Reference", items: [{ autogenerate: { directory: "reference" } }] },
        { label: "Syllabus", link: "/syllabus/" },
        { label: "Changelog", link: "/changelog/" },
      ],
    }),
  ],
});
