import { readFileSync } from "node:fs";
import { resolve } from "node:path";

/** Repo root, relative to the site/ directory where Astro runs. */
export const REPO_ROOT = resolve(process.cwd(), "..");

/** Read a file from the repo. Throws (and fails the build) if it doesn't exist. */
export function readRepoFile(path: string): string {
  return readFileSync(resolve(REPO_ROOT, path), "utf8");
}

export const GITHUB_BLOB = "https://github.com/pragmaticarun/ai-native-course/blob/main/";
