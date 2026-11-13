import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["examples/ts/**/*.test.ts", "exercises/**/ts/**/*.test.ts"],
    env: { COURSE_LLM_PROVIDER: "mock" },
  },
});
