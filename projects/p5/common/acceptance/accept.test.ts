// Hidden acceptance tests (the ground truth), copied into the repo only while judging.
import assert from "node:assert/strict";
import { test } from "node:test";
import { formatBytes, slugify, truncate } from "../src/format.ts";

test("bytes", () => {
  assert.equal(formatBytes(1536), "1.5 KB");
  assert.equal(formatBytes(1000), "1000 B");
  assert.equal(formatBytes(5 * 1024 * 1024), "5.0 MB");
});
test("slug", () => assert.equal(slugify("  Hello, World! "), "hello-world"));
test("truncate", () => {
  assert.equal(truncate("abcdef", 4), "abc…");
  assert.equal(truncate("abc", 4), "abc");
});
