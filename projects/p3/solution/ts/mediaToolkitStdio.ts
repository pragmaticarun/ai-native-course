// stdio entry: node --experimental-strip-types projects/p3/solution/ts/mediaToolkitStdio.ts <media-root>
import { serveStdio } from "@modelcontextprotocol/server/stdio";
import { buildMediaToolkit } from "./mediaToolkit.ts";

serveStdio(() => buildMediaToolkit(process.argv[2] ?? "."));
