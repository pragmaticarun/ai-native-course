// stdio entry for the TypeScript media-probe server:
//   node --experimental-strip-types examples/ts/m9/mediaProbeStdio.ts <media-root>
// `serveStdio` takes a factory and picks the protocol era from the client's opening
// message (2026-07-28 via server/discover, or a 2025-era initialize). A hand-wired
// `server.connect(new StdioServerTransport())` serves the 2025 era only (SDK 2.4.0).
import { unlinkSync } from "node:fs";
import { serveStdio } from "@modelcontextprotocol/server/stdio";
import { buildMediaProbe, ffmpegRunner } from "./mediaProbe.ts";

const root = process.argv[2] ?? ".";
serveStdio(() => buildMediaProbe(root, ffmpegRunner, unlinkSync));
