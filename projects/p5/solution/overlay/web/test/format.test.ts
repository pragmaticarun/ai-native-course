import assert from "node:assert/strict";
import { test } from "node:test";
import { formatBytes, slugify, truncate } from "../src/format.ts";

test("formatBytes uses 1024 and stays in bytes below it", () => {
  assert.equal(formatBytes(1000), "1000 B");
  assert.equal(formatBytes(1536), "1.5 KB");
});

test("slugify drops punctuation at both ends", () => {
  assert.equal(slugify("  Hello, World! "), "hello-world");
});

test("truncate keeps short text and fits the ellipsis inside max", () => {
  assert.equal(truncate("abc", 4), "abc");
  assert.equal(truncate("abcdef", 4).length, 4);
});
