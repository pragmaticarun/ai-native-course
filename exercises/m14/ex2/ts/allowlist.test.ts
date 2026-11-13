import { expect, test } from "vitest";

const variant = process.env.EXERCISE_VARIANT ?? "solution";
const { checkArgs } = (await import(`./${variant}/allowlist.ts`)) as typeof import("./solution/allowlist.ts");
const ROOT = "/media";

test("a normal trim + loudnorm call is allowed", () => {
  expect(checkArgs(["-ss", "1.5", "-t", "3", "-i", "in/a.mp4", "-af", "loudnorm=I=-16", "-c:v", "libx264", "out/a.mp4"], ROOT)).toEqual([]);
});

test("-f and -filter_complex are not on the allowlist", () => {
  expect(checkArgs(["-f", "concat", "-i", "list.txt", "o.mp4"], ROOT)).toEqual(["option not allowed: -f", "option not allowed: concat"]);
  expect(checkArgs(["-i", "a.mp4", "-filter_complex", "[0]null", "o.mp4"], ROOT)[0]).toBe("option not allowed: -filter_complex");
});

test("protocol tricks in inputs and outputs", () => {
  expect(checkArgs(["-i", "concat:a.mp4|/etc/passwd", "o.mp4"], ROOT)).toEqual(["protocol not allowed: concat:a.mp4|/etc/passwd"]);
  expect(checkArgs(["-i", "http://evil.example/x.m3u8", "o.mp4"], ROOT)).toEqual(["protocol not allowed: http://evil.example/x.m3u8"]);
  expect(checkArgs(["-i", "a.mp4", "tcp://1.2.3.4:9000"], ROOT)).toEqual(["protocol not allowed: tcp://1.2.3.4:9000"]);
});

test("path escapes", () => {
  expect(checkArgs(["-i", "../../etc/passwd", "o.mp4"], ROOT)).toEqual(["path escapes root: ../../etc/passwd"]);
  expect(checkArgs(["-i", "a.mp4", "/tmp/o.mp4"], ROOT)).toEqual(["path escapes root: /tmp/o.mp4"]);
  expect(checkArgs(["-i", "in/../a.mp4", "o.mp4"], ROOT)).toEqual([]);
});

test("filters that open files or take remote commands", () => {
  expect(checkArgs(["-i", "a.mp4", "-vf", "movie=/etc/passwd[w];[in][w]overlay", "o.mp4"], ROOT)).toEqual(["filter not allowed: movie"]);
  expect(checkArgs(["-i", "a.mp4", "-af", "volume=2,azmq", "o.mp4"], ROOT)).toEqual(["filter not allowed: azmq"]);
  expect(checkArgs(["-i", "a.mp4", "-vf", "scale=640:-2", "o.mp4"], ROOT)).toEqual([]);
});
